import json
from collections import defaultdict

import flask
import requests
import yaml


#
# Set up globals
#

CONFIG = "config.yml"
with open(CONFIG) as fd:
    config = yaml.load(fd)

app = flask.Flask(__name__)


#
# Helpers/utils
#

def metrics(queries, leaves_only=False):
    """
    Return list of metric paths based on one or more search queries.

    Basically just a wrapper around Graphite's /metrics/expand/ endpoint.
    """
    query = "?" + "&".join(map(lambda x: "query=%s" % x, queries))
    url = config['graphite_url'] + "/metrics/expand/%s" % query
    if leaves_only:
        url += "&leavesOnly=1"
    response = requests.get(url)
    struct = json.loads(response.content)['results']
    filtered = filter(lambda x: x not in config['hosts']['exclude'], struct)
    return filtered

def nested_metrics(base, max_depth=7):
    """
    Return *all* metrics starting with the given ``base`` pattern/string.

    Assumes maximum realistic depth of ``max_depth``, due to the method
    required to get multiple levels of metric paths out of Graphite.

    If run with ``base="*"`` be prepared to wait a very long time for any
    nontrivial Graphite installation to come back with the answer...
    """
    queries = []
    for num in range(1, max_depth + 1):
        query = "%s.%s" % (base, ".".join(['*'] * num))
        queries.append(query)
    return metrics(queries, leaves_only=True)

def groupings():
    return sorted(config['metrics'].keys())


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
    hosts = metrics("*")
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
        metrics=config['metrics'][group],
        groupings=groupings(),
        current=group,
    )

@app.route('/render/')
def render():
    url = config['graphite_url'] + "/render/"
    response = requests.get(url, params=flask.request.args)
    r = flask.Response(
        response=response.raw,
        headers=response.headers,
    )
    return r
