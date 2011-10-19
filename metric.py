from collections import defaultdict
from types import StringTypes


def combine(paths, expansions=[]):
    """
    Take a list of paths and combine into fewer using brace-expressions.

    E.g. ["foo.bar", "foo.biz"] => "foo.{bar,biz}"
    """
    buckets = defaultdict(list)
    for path in paths:
        for i, part in enumerate(path.split('.')):
            if part not in buckets[i]:
                buckets[i].append(part)
    ret = [[]]
    for key in sorted(buckets.keys()):
        value = list(buckets[key])
        if len(value) == 1:
            for x in ret:
                x.append(value[0])
        else:
            if key in expansions:
                previous = ret[:]
                ret = []
                for x in value:
                    for y in previous:
                        ret.append(y + [x])
            else:
                joined = "{" + ",".join(value) + "}"
                for x in ret:
                    x.append(joined)
    result = map(lambda x: '.'.join(x), ret)
    return result


class Metric(object):
    """
    Beefed-up metric object capable of substituting wildcards and more!
    """
    def __init__(self, struct, graphite):
        """
        Use ``struct`` to become a metric referring to ``graphite`` backend.
        """
        self.graphite = graphite
        options = {
            'exclude': [],
            'expand': [],
        }
        # Non-dicts are assumed to be simple stringlike paths
        if not hasattr(struct, "keys"):
            self.path = struct
        # Dicts should have one key only, whose value is a dict of options
        else:
            if len(struct) > 1:
                raise ValueError("Found metric value which is a dict but has >1 key! Please make sure your metrics list consists only of strings and one-item dicts.")
            self.path, local_options = struct.items()[0]
            options = dict(options, **(local_options or {}))
        # Generate split version of our path, and note any wildcards
        self.parts = self.path.split('.')
        self.wildcards = self.find_wildcards()
        # Normalize/clean up options
        self.excludes = self.set_excludes(options['exclude'])
        self.to_expand = self.set_expansions(options['expand'])

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
        if not hasattr(excludes, "keys"):
            excludes = {0: excludes}
        return excludes

    def set_expansions(self, expansions):
        if expansions == "all":
            expansions = self.wildcards 
        return expansions

    def expand(self, hostname=None):
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
        if hostname:
            path = sep.join([hostname, self.path])
            func = lambda x: sep.join(x.split(sep)[1:])
        else:
            path = self.path
            func = lambda x: x
        return map(func, self.graphite.query(path))

    def normalize(self, hostname=None):
        """
        Return a list of one or more metric paths based on our options.

        For example, a basic ``Metric("foo.*")`` with no options would
        normalize into simply ``["foo.*"]``. ``Metric("foo.*", {'exclude':
        [1,2]})`` would expand out, remove any matching exclusions, compress
        again, and return e.g. ``["foo.{3,4,5}]``. And ``Metric("foo.*",
        {'expand': 'true'})`` would cause full expansion, returning e.g.
        ``["foo.1", "foo.2", "foo.3", ...]``.
        """
        # Not applying any filters == just the path
        if not self.excludes:
            return [self.path]
        # Expand out to full potential list of paths, apply filters
        matches = []
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
                matches.append(item)
        # Perform any necessary combining into brace-expressions & return
        return combine(matches, self.to_expand)

