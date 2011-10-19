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
            self.excludes = self.set_excludes(options['exclude'])
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

    def set_excludes(self, excludes):
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

        This method does not take into account any filtering or exclusions; it
        returns the largest possible expansion (basically what Graphite's
        /metrics/expand/ endpoint gives you.)

        ``hostname`` is used solely for giving context to the expansion; the
        returned metric paths will still be host-agnostic (in order to blend in
        with non-expanded metric paths.)
        """
        sep = '.'
        return map(
            lambda x: sep.join(x.split(sep)[1:]),
            self.graphite.query(sep.join([hostname, self.path]))
        )

    def normalize(self, hostname):
        """
        Return a list of one or more metric paths based on our options.

        For example, a basic ``Metric("foo.*")`` with no options would
        normalize into simply ``["foo.*"]``. But ``Metric("foo.*", {'exclude':
        [1,2]})`` would expand out, remove any matching exclusions, and return
        e.g. ``["foo.3", "foo.4", "foo.5"]``.
        """
        if not self.excludes:
            return [self.path]
        ret = []
        for item in self.expand(hostname):
            parts = item.split('.')
            good = True
            for location, part in enumerate(parts):
                # We only care about wildcard slots
                if location not in self.wildcards:
                    continue
                # Which wildcard slot is this?
                wildcard_index = self.wildcards.index(location)
                # Is this substring listed for exclusion in this slot?
                if part in self.excludes.get(wildcard_index, []):
                    good = False
                    break # move on to next metric/item
            if good:
                ret.append(item)
        return ret
