from collections import defaultdict
import operator
import os

import requests
import flask
import yaml

from metric import Metric
from graphite import Graphite
from config import Config


#
# Set up globals
#

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.yml")
with open(CONFIG) as fd:
    config = Config(fd.read())

app = flask.Flask(__name__)


#
# Helpers/utils
#

def groupings():
    return sorted(config.groups.keys())


#
# Template filters
#

@app.template_filter('dots')
def dots(s):
    return s.replace('_', '.')

@app.template_filter('render')
def _render(graph, **overrides):
    """
    Takes a Graph as input, prints out full render URL.
    """
    return flask.url_for("render", **graph.kwargs)

@app.template_filter('composer')
def composer(graph):
    return config.graphite.uri + "/composer/" + graph.querystring


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

@app.route('/hosts/<hostname>/<group>/<period>/')
def grouping(hostname, group, period):
    # Get metric objects for this group
    raw_metrics = config.groups[group].values()
    # Filter period value through defined aliases
    kwargs = {'from': config.periods.get(period, period)}
    # Generate graph objects from each metric, based on hostname context
    graphs = map(lambda m: m.graphs(hostname, **kwargs), raw_metrics)
    merged = reduce(operator.add, graphs, [])
    return flask.render_template(
        'host.html',
        hostname=hostname,
        metrics=merged,
        groupings=groupings(),
        periods=config.periods.keys(),
        current_group=group,
        current_period=period
    )

@app.route('/render/')
def render():
    uri = config.graphite.uri + "/render/"
    response = requests.get(uri, params=flask.request.args)
    return flask.Response(response=response.raw, headers=response.headers)
