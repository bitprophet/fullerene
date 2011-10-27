class Graph(object):
    def __init__(self, hostname, path, children=(), config=None, **kwargs):
        """
        hostname: hostname part of metric path
        path: rest of metric path to query Graphite for when rendering
        children: list of constituent non-globbed paths
        config: config object for querying
        kwargs: graph drawing options such as 'from'
        """
        # Basic init
        children = children or []
        self.path = path
        self.hostname = hostname

        # Children are (potential) graphs of their own, for now just used for
        # stats info.
        self.children = map(
            lambda x: Graph(hostname, x, (), config, **kwargs),
            children
        )

        # Add default title
        if 'title' not in kwargs:
            period = " (%s)" % kwargs['from'] if 'from' in kwargs else ""
            kwargs['title'] = str(self) + period
        kwargs['target'] = "%s.%s" % (self.hostname, self.path)
        self.kwargs = kwargs

        # Store data about what our graph shows (e.g. min/max)
        # (but only if we're a single real metric path, i.e. no children)
        if config and not children:
            for name, value in config.graphite.stats(kwargs).items():
                setattr(self, name, value)

    def __str__(self):
        return self.path

    def __repr__(self):
        return "<Graph %r: %r (%r)>" % (
            str(self), self.children, self.kwargs
        )

    @property
    def querystring(self):
        """
        Prints out query string for easy appending to URLs.

        E.g. "?target=foo&from=blah&height=xxx"
        """
        pairs = map(lambda x: "%s=%s" % (x[0], x[1]), self.kwargs.items())
        return "?" + "&".join(pairs)
