import json
import pprint

import flask
import requests


INTERNAL = "http://localhost"
EXTERNAL = "https://monitor2.whiskeymedia.com"

app = flask.Flask(__name__)

def metrics(query):
    response = requests.get(INTERNAL + "/metrics/expand/?query=%s" % query)
    struct = json.loads(response.content)
    return struct['results']


@app.route('/')
def index():
    return flask.render_template('index.html', hosts=metrics("*"))

@app.route('/hosts/<hostname>/')
def host(hostname):
    return format(metrics("%s.*" % hostname))


if __name__ == "__main__":
    app.run(host='localhost', port=8080, debug=True)
