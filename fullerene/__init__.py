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

def metrics_for_group(name, hostname):
    raw_metrics = config.groups[name].values()
    members = map(lambda x: x.normalize(hostname), raw_metrics)
    merged = reduce(operator.add, members, [])
    return merged


#
# Template filters
#

@app.template_filter('dots')
def dots(s):
    return s.replace('_', '.')

@app.template_filter('render')
def _render(metric, hostname, **overrides):
    """
    Takes a DisplayMetric as input, prints out full render URL
    """
    params = metric.render_params(hostname, **overrides)
    return flask.url_for("render", **params)


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
    return flask.render_template(
        'host.html',
        hostname=hostname,
        metrics=metrics_for_group(group, hostname),
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
