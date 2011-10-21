from collections import defaultdict
import operator

import requests
import flask
import yaml

from metric import Metric
from graphite import Graphite
from config import Config


#
# Set up globals
#

CONFIG = "config.yml"
with open(CONFIG) as fd:
    config = Config(fd.read())

app = flask.Flask(__name__)


#
# Helpers/utils
#

def groupings():
    return sorted(config.groups.keys())

def metrics_for_group(name, hostname):
    raw_metrics = config.groups[name]
    members = map(lambda x: Metric(x, config).normalize(hostname), raw_metrics)
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
    kwargs = dict(config.defaults, **overrides)
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
    hosts = config.graphite.query("*")
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
    uri = config.graphite.uri + "/render/"
    response = requests.get(uri, params=flask.request.args)
    return flask.Response(response=response.raw, headers=response.headers)
