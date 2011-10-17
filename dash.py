import json
import pprint
from collections import defaultdict

import flask
import requests
import yaml


with open("config.yml") as fd:
    config = yaml.load(fd)

DEFAULT_HOST_METRICS = (
    'df.root.df_complex.free.value',
    'df.mnt.df_complex.free.value',
    'disk.xvda1.disk_octets.{read,write}',
    'disk.xvdb.disk_octets.{read,write}',
    'interface.if_octets.eth0.{rx,tx}',
    'load.load.{shortterm,midterm,longterm}',
    'memory.memory.free.value',
)

app = flask.Flask(__name__)

def metrics(queries, leaves_only=False):
    query = "?" + "&".join(map(lambda x: "query=%s" % x, queries))
    url = config['graphite_urls']['internal'] + "/metrics/expand/%s" % query
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


@app.route('/')
def index():
    hosts = metrics("*")
    domains = defaultdict(list)
    for host in hosts:
        name, _, domain = host.partition('_')
        domains[domain].append(name)
    domains = sorted(domains.iteritems())
    return flask.render_template('index.html', domains=domains)

@app.route('/hosts/<hostname>/')
def host(hostname):
    all_metrics = nested_metrics(hostname)
    return flask.render_template(
        'host.html',
        hostname=hostname,
        all_metrics=all_metrics,
        base_metrics=DEFAULT_HOST_METRICS,
        baseurl=config['graphite_urls']['external']
    )


if __name__ == "__main__":
    app.run(host='localhost', port=8080, debug=True)
