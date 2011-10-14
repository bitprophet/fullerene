import json
import pprint

import flask
import requests


INTERNAL = "http://localhost"
EXTERNAL = "https://monitor2.whiskeymedia.com"

app = flask.Flask(__name__)

def metrics(queries, leaves_only=False):
    query = "?" + "&".join(map(lambda x: "query=%s" % x, queries))
    url = INTERNAL + "/metrics/expand/%s" % query
    if leaves_only:
        url += "&leavesOnly=1"
    response = requests.get(url)
    struct = json.loads(response.content)
    return struct['results']

def nested_metrics(base):
    MAX=7
    queries = []
    for num in range(1, MAX + 1):
        query = "%s.%s" % (base, ".".join(['*'] * num))
        queries.append(query)
    return metrics(queries, leaves_only=True)


@app.route('/')
def index():
    return flask.render_template('index.html', hosts=metrics("*"))

@app.route('/hosts/<hostname>/')
def host(hostname):
    data = nested_metrics(hostname)
    baseurl = "%s/render?target=" % EXTERNAL
    return flask.render_template('host.html', metrics=data, baseurl=baseurl)


if __name__ == "__main__":
    app.run(host='localhost', port=8080, debug=True)
