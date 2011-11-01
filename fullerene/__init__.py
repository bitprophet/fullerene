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

ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG = os.path.join(ROOT, "config.yml")
with open(CONFIG) as fd:
    config = Config(fd.read())

app = flask.Flask(__name__)


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
    if config.external_graphite:
        return config.external_graphite + "/composer/" + graph.querystring


#
# Routes
#

@app.route('/')
def index():
    collections = [(
        'All hosts, by domain name',
        flask.url_for('by_domain')
    )]
    for slug, data in config.collections.items():
        collections.append((
            data['title'],
            flask.url_for('collection', collection=slug)
        ))
    return flask.render_template(
        'index.html',
        collections=collections
    )

@app.route('/by_domain/')
def by_domain():
    # Built-in introspection-driven by-domain collection
    hosts = config.graphite.query("*")
    domains = defaultdict(list)
    for host in hosts:
        name, _, domain = host.partition('_')
        domains[domain].append(host.replace('_', '.'))
    return flask.render_template(
        'by_domain.html',
        domains=domains,
        metric_groups=config.metric_groups,
    )

@app.route('/<collection>/')
def collection(collection):
    pass

@app.route('/<host>/<metric_group>/<period>/')
def host_metrics(host, metric_group, period):
    # Get metric objects for this group
    raw_metrics = config.groups[metric_group].values()
    # Filter period value through defined aliases
    kwargs = {'from': config.periods.get(period, period)}
    # Switch to underscores if needed
    if '.' in host:
        host = host.replace('.', '_')
    # Generate graph objects from each metric, based on hostname context
    graphs = map(lambda m: m.graphs(host, **kwargs), raw_metrics)
    merged = reduce(operator.add, graphs, [])
    return flask.render_template(
        'host.html',
        host=host,
        metrics=merged,
        metric_groups=config.metric_groups,
        periods=config.periods.keys(),
        current_group=metric_group,
        current_period=period,
    )

@app.route('/render/')
def render():
    uri = config.graphite.uri + "/render/"
    response = requests.get(uri, params=flask.request.args)
    return flask.Response(response=response.raw, headers=response.headers)
