import json
import pprint
from collections import defaultdict
import urllib

import flask
import requests
import yaml
import werkzeug


#
# Set up globals
#

with open("config.yml") as fd:
    config = yaml.load(fd)

app = flask.Flask(__name__)


#
# Helpers/utils
#

def metrics(queries, leaves_only=False):
    query = "?" + "&".join(map(lambda x: "query=%s" % x, queries))
    url = config['graphite_url'] + "/metrics/expand/%s" % query
    if leaves_only:
        url += "&leavesOnly=1"
    response = requests.get(url)
    struct = json.loads(response.content)['results']
    filtered = filter(lambda x: x not in config['hosts']['exclude'], struct)
    return filtered

def nested_metrics(base):
    MAX = 7
    queries = []
    for num in range(1, MAX + 1):
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


#
# Routes
#

@app.route('/render/')
def render():
    url = config['graphite_url'] + "/render/"
    response = requests.get(url, params=flask.request.args)
    r = flask.Response(
        response=response.raw,
        headers=werkzeug.Headers(response.headers),
        direct_passthrough=True
    )
    return r

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

@app.route('/hosts/<hostname>/')
def host(hostname):
    all_metrics = nested_metrics(hostname)
    return flask.render_template(
        'host.html',
        hostname=hostname,
        all_metrics=all_metrics,
        base_metrics=config['metrics']['baseline'],
    )

@app.route('/hosts/<hostname>/<group>/')
def grouping(hostname, group):
    return flask.render_template(
        'host.html',
        hostname=hostname,
        metrics=config['metrics'][group],
        groupings=groupings(),
        current=group,
        get_params=urllib.urlencode(config['defaults'])
    )


#
# Runner
#

if __name__ == "__main__":
    app.run(host='localhost', port=8080, debug=True)
