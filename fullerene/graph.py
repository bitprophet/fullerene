class Graph(object):
    def __init__(
            self,
            hostname,
            path,
            config=None,
            title=None,
            title_param=None,
            **kwargs
        ):
        """
        hostname: hostname part of metric path
        path: rest of metric path to query Graphite for when rendering
        config: config object for querying
        kwargs: graph drawing options such as 'from'
        """
        # Basic init
        self.path = path
        self.hostname = hostname
        self.title = title
        self.title_param = title_param

        # Add default title
        if 'title' not in kwargs:
            period = " (%s)" % kwargs['from'] if 'from' in kwargs else ""
            param = ""
            if self.title_param:
                param = " (%s)" % self.path.split('.')[self.title_param]
            kwargs['title'] = (self.title + param) if self.title else self.path
        # Try to squeeze in hostname after any potential function applications
        print ">>> self.hostname: %r, self.path: %r" % (self.hostname, self.path)
        if '(' in self.path:
            i = self.path.rfind('(') + 1
            path = self.path[:i] + self.hostname + '.' + self.path[i:]
        else:
            path = self.hostname + "." + self.path
        print "??? path now: %r" % path
        kwargs['target'] = path
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
