from collections import defaultdict
import operator
import os

import requests
import flask
import yaml

from metric import Metric
from graphite import Graphite
from config import Config
from utils import dots, sliced


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
def dots_(string):
    return dots(string)

@app.template_filter('dot')
def dot_(string, *args):
    return sliced(string, *args) or string

@app.template_filter('render')
def _render(graph, **overrides):
    """
    Takes a Graph as input, prints out full render URL.
    """
    params = dict(graph.kwargs, **overrides)
    return flask.url_for("render", **params)

@app.template_filter('composer')
def composer(graph):
    """
    We don't typically want this to accept overrides -- if somebody wants to go
    to the composer view, many e.g. thumbnail/presentational options should
    probably get turned off so they get a more normal view. Useful things like
    timeperiod/from will typically be preserved.
    """
    if config.external_graphite:
        return config.external_graphite + "/composer/" + graph.querystring


#
# Routes
#

@app.route('/')
def index():
    collections = [
        ('by_domain', {
            'title': 'Per-host pages, by domain',
            'groups': config.graphite.hosts_by_domain(),
        })
    ]
    collections.extend(
        sorted(
            config.collections.items(),
            key=lambda x: x[0]
        )
    )
    return flask.render_template(
        'index.html',
        collections=collections
    )

@app.route('/by_domain/<domain>/')
def domain(domain):
    return flask.render_template(
        'domain.html',
        domain=domain,
        hosts=config.graphite.hosts_for_domain(domain),
        metric_groups=config.metric_groups,
    )

@app.route('/<collection>/<group>/')
def group(collection, group):
    cname = collection
    gname = group
    collection = config.collections[collection]
    group = collection['groups'][group]
    return flask.render_template(
        'collection_group.html',
        cname=cname,
        group=group,
        metrics=group['metrics']
    )

@app.route('/<collection>/<group>/<metric>/')
def group_metric(collection, group, metric):
    # Basic setup
    period = '-4hours'
    cname = collection
    collection = config.collections[collection]
    gname = group
    group = collection['groups'][group]
    # Slug => metric object
    mobj = None
    for m in group['metrics']:
        if m.name == metric:
            mobj = m
            break
    if mobj is None:
        flask.abort(404)
    # Metric-based nav
    metric_groups = map(
        lambda x: (x, flask.url_for('group_metric', collection=cname,
            group=gname, metric=x)),
        [x.name for x in group['metrics']]
    )
    parent = flask.url_for('group', collection=cname, group=gname)
    # Grid setup
    per_row = 5
    col_size = (16 / per_row)
    # Thumbnails
    thumbnail_opts = {
        'height': 100,
        'width': 200,
        'hideLegend': True,
        'hideGrid': True,
        'yBoundsOnly': True,
        'hideXAxis': True,
        'from': period,
    }
    return flask.render_template(
        'group.html',
        collection=collection,
        group=group,
        metric=mobj,
        metric_groups=metric_groups,
        current_mgroup=metric,
        per_row=per_row,
        col_size=col_size,
        thumbnail_opts=thumbnail_opts,
        period=period,
        parent=parent
    )

@app.route('/by_domain/<domain>/<host>/<metric_group>/<period>/')
def host(domain, host, metric_group, period):
    # Get metric objects for this group
    raw_metrics = config.groups[metric_group].values()
    # Filter period value through defined aliases
    kwargs = {'from': config.periods.get(period, period)}
    # Generate graph objects from each metric, based on hostname context
    graphite_host = host + '_' + domain.replace('.', '_')
    graphs = map(lambda m: m.graphs(graphite_host, **kwargs), raw_metrics)
    merged = reduce(operator.add, graphs, [])
    # Set up metric group nav
    metric_groups = map(
        lambda x: (x, flask.url_for('host', domain=domain, metric_group=x,
            host=host, period=period)),
        config.metric_groups
    )
    return flask.render_template(
        'host.html',
        domain=domain,
        host=host,
        metrics=merged,
        metric_groups=metric_groups,
        periods=config.periods.keys(),
        current_mgroup=metric_group,
        current_period=period,
    )

@app.route('/render/')
def render():
    uri = config.graphite.uri + "/render/"
    response = requests.get(uri, params=flask.request.args)
    return flask.Response(response=response.raw, headers=response.headers)
