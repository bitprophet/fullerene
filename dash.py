import json
import pprint
from collections import defaultdict

import flask
import requests


INTERNAL = "http://localhost"
EXTERNAL = "https://monitor2.whiskeymedia.com"
EXCLUDE_HOSTS = ("carbon",)

app = flask.Flask(__name__)

def metrics(queries, leaves_only=False):
    query = "?" + "&".join(map(lambda x: "query=%s" % x, queries))
    url = INTERNAL + "/metrics/expand/%s" % query
    if leaves_only:
        url += "&leavesOnly=1"
    response = requests.get(url)
    struct = json.loads(response.content)['results']
    filtered = filter(lambda x: x not in EXCLUDE_HOSTS, struct)
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
    data = nested_metrics(hostname)
    return flask.render_template('host.html', metrics=data, baseurl=EXTERNAL)


if __name__ == "__main__":
    app.run(host='localhost', port=8080, debug=True)
