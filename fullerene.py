from collections import defaultdict
import operator

import requests
import flask
import yaml

from metric import Metric
from graphite import Graphite


#
# Set up globals
#

CONFIG = "config.yml"
with open(CONFIG) as fd:
    config = yaml.load(fd)

app = flask.Flask(__name__)
graphite = Graphite(config)


#
# Helpers/utils
#



def groupings():
    return sorted(config['metrics'].keys())

def expand_metric(metric, hostname):
    """
    Take metric string or one-key dict and normalize to an iterable as needed.

    Each item in the iterable will be a Graphite metric string mapping to a
    single graph. These strings themselves may contain wildcards, etc, as
    defined in the Graphite URL API.

    This function's purpose is to read YAML config metadata and optionally
    break down a config chunk into >1 Graphite metric string. This allows us to
    exclude, filter etc without requiring support for new syntax in Graphite.

    String inputs just come out as [metric] (i.e. normalization to list.)

    Dict inputs should have a single string key; basically, mixed strings and
    dicts should come from YAML that looks like this::
    
        metrics:
            - metric1.foo.bar
            - metric2.biz.baz
            - metric3.blah.blah:
                option: value
                option2: value2
            - metric4.whatever

    All "items" under ``metrics`` are metric paths; the difference is that they
    may optionally have configuration options, which turns that entry into a
    dict.

    Dict inputs will also come out as at least [metric] (in this case, the
    single dict key) but config options will often cause multiple metrics to be
    output, e.g. [metric1, metric2], due to filtering/excluding requiring us to
    ask Graphite for the full expansion up-front, and then manipulating that
    result.

    Options currently implemented:

    * ``exclude``: a list of explicit matches to exclude from the first
      wildcard. E.g. a metric ``df.*.free`` which expands, in Graphite, to
      [df.root.free, df.mnt.free, df.dev.free, df.dev-shm.free], may be
      filtered to remove some specific matches like so::

        metrics:
            - df.*.free: [dev, dev-shm]

      Such a setup would result in a return value from this function of
      [df.root.free, df.mnt.free] given the expansion example above.

      Note that partial wildcards work the same way; the logic operates based
      on metric sections (i.e. separated by periods) containing wildcards
      (meaning asterisks; curly-brace expansion is not considered a wildcard
      here.)

      If multiple wildcards are given, and the value is still just one list, it
      will only apply to the first wildcard. To pair specific exclusion lists
      with specific wildcard positions, use a dict value instead, with numeric
      keys matching the wildcard positions (0-indexed.) E.g.::

        metrics:
            - foo.*.bar.*:
              0: [these, are, excluded, from, 1st, wildcard]
              1: [these, from, the, 2nd]
    """
    metric = Metric(metric, graphite)
    # Exclude
    ret = []
    for item in metric.expand(hostname):
        parts = item.split('.')
        good = True
        for location, part in enumerate(parts):
            # We only care about wildcard slots
            if location not in metric.wildcards:
                continue
            # Which wildcard slot is this?
            wildcard_index = metric.wildcards.index(location)
            # Is this substring listed for exclusion in this slot?
            if part in metric.excludes.get(wildcard_index, []):
                good = False
                break # move on to next metric/item
        if good:
            ret.append(item)
    return ret

def metrics_for_group(name, hostname):
    raw_metrics = config['metrics'][name]
    members = map(lambda x: expand_metric(x, hostname), raw_metrics)
    merged = reduce(operator.add, members, [])
    return merged


#
# Template filters
#

@app.template_filter('dots')
def dots(s):
    return s.replace('_', '.')

@app.template_filter('render')
def _render(hostname, metric, **overrides):
    """
    Use: {{ hostname|render(metric, from='-2hours', height=400, ...) }}

    Will filter the 'from' kwarg through config['periods'] first.

    Also sets a default 'title' kwarg to metric + period/from.
    """
    # Merge with defaults from config
    kwargs = dict(config['defaults'], **overrides)
    # Set a default (runtime) title
    if 'title' not in kwargs:
        kwargs['title'] = "%s (%s)" % (metric, kwargs['from'])
    # Translate period names in 'from' kwarg if needed
    f = kwargs['from']
    kwargs['from'] = config['periods'].get(f, f)
    return flask.url_for(
        'render',
        target="%s.%s" % (hostname, metric),
        **kwargs
    )


#
# Routes
#

@app.route('/')
def index():
    hosts = graphite.query("*")
    domains = defaultdict(list)
    for host in hosts:
        name, _, domain = host.partition('_')
        domains[domain].append(name)
    domains = sorted(domains.iteritems())
    return flask.render_template(
        'index.html',
        domains=domains,
        groupings=groupings()
    )

@app.route('/hosts/<hostname>/<group>/')
def grouping(hostname, group):
    return flask.render_template(
        'host.html',
        hostname=hostname,
        metrics=metrics_for_group(group, hostname),
        groupings=groupings(),
        current=group,
    )

@app.route('/render/')
def render():
    url = config['graphite_url'] + "/render/"
    response = requests.get(url, params=flask.request.args)
    return flask.Response(response=response.raw, headers=response.headers)
