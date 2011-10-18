class Metric(object):
    """
    Beefed-up metric object capable of substituting wildcards and more!
    """
    def __init__(self, struct, graphite):
        """
        Use ``struct`` to become a metric referring to ``graphite`` backend.
        """
        self.graphite = graphite
        self.excludes = {}
        # Non-dicts are assumed to be simple stringlike paths
        if not hasattr(struct, "keys"):
            self.path = struct
        # Dicts should have one key only, whose value is a dict of options
        else:
            if len(struct) > 1:
                raise ValueError("Found metric value which is a dict but has >1 key! Please make sure your metrics list consists only of strings and one-item dicts.")
            self.path, options = struct.items()[0]
            self.excludes = self.normalize_excludes(options['exclude'])
        # Generate split version of our path, and note any wildcards
        self.parts = self.path.split('.')
        self.wildcards = self.find_wildcards()

    def find_wildcards(self):
        """
        Fill in self.wildcards from self.parts
        """
        # Discover wildcard locations (so we can tell, while walking a split
        # string, "which" wildcard we may be looking at (the 0th, 1st, Nth)
        wildcards = []
        for index, part in enumerate(self.parts):
            if '*' in part:
                wildcards.append(index)
        return wildcards

    def normalize_excludes(self, excludes):
        """
        Translate from-YAML dict into our object's API
        """
        # Excludes
        if not hasattr(excludes, "keys"):
            excludes = {0: excludes}
        return excludes

    def expand(self, hostname):
        """
        Return expanded metric list from our path and the given ``hostname``.

        E.g. if self.path == foo.*.bar, this might return [foo.1.bar,
        foo.2.bar].

        ``hostname`` is used solely for giving context to the expansion; the
        returned metric paths will still be host-agnostic (in order to blend in
        with non-expanded metric paths.)
        """
        sep = '.'
        return map(
            lambda x: sep.join(x.split(sep)[1:]),
            self.graphite.query(sep.join([hostname, self.path]))
        )
