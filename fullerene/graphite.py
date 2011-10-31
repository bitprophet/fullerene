import json
import requests


class Graphite(object):
    """
    Stand-in for the backend Graphite server/service.

    Mostly used for querying API endpoints under /metrics/.
    """
    def __init__(self, uri, exclude_hosts):
        self.uri = uri
        self.exclude_hosts = exclude_hosts

    def query(self, *paths, **kwargs):
        """
        Return list of metric paths based on one or more search queries.

        Basically just a wrapper around Graphite's /metrics/expand/ endpoint.

        Specify ``leaves_only=True`` to filter out any non-leaf results.
        """
        query = "?" + "&".join(map(lambda x: "query=%s" % x, paths))
        uri = self.uri + "/metrics/expand/%s" % query
        if kwargs.get('leaves_only', False):
            uri += "&leavesOnly=1"
        response = requests.get(uri)
        struct = json.loads(response.content)['results']
        filtered = filter(
            lambda x: x not in self.exclude_hosts,
            struct
        )
        return filtered

    def stats(self, kwargs):
        kwargs = dict(kwargs) # lest we screw it up for rendering later
        kwargs['format'] = 'json'
        uri = "%s/render/" % self.uri
        return json.loads(requests.get(uri, params=kwargs).content)

    def query_all(base, max_depth=7):
        """
        Return *all* metrics starting with the given ``base`` pattern/string.

        Assumes maximum realistic depth of ``max_depth``, due to the method
        required to get multiple levels of metric paths out of Graphite.

        If run with ``base="*"`` be prepared to wait a very long time for any
        nontrivial Graphite installation to come back with the answer...
        """
        queries = []
        for num in range(1, max_depth + 1):
            query = "%s.%s" % (base, ".".join(['*'] * num))
            queries.append(query)
        return self.query(queries, leaves_only=True)
