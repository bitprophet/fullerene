class Graph(object):
    def __init__(
            self,
            path,
            config=None,
            title=None,
            title_param=None,
            **kwargs
        ):
        """
        path: metric path to query Graphite for when rendering (includes host)
        config: config object for querying
        kwargs: graph drawing options such as 'from'
        """
        # Basic init
        self.path = path
        self.title = title
        self.title_param = title_param

        # Add default title
        if 'title' not in kwargs:
            period = " (%s)" % kwargs['from'] if 'from' in kwargs else ""
            param = ""
            if self.title_param:
                param = " (%s)" % self.path.split('.')[self.title_param]
            kwargs['title'] = (self.title + param) if self.title else self.path

        # Construct final target path
        path = self.path
        function = kwargs.pop('function', None)
        if function:
            path = "%s(%s)" % (function, path)
        kwargs['target'] = path

        # Set kwargs for drawing
        self.kwargs = kwargs

        # Store data about what our graph shows (e.g. min/max)
        if config:
            self.stats = config.graphite.stats(kwargs)

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
