from collections import defaultdict
from types import StringTypes

from graph import Graph


def combine(paths, expansions=[], include_raw=False):
    """
    Take a list of paths and combine into fewer using brace-expressions.

    E.g. ["foo.bar", "foo.biz"] => "foo.{bar,biz}"

    When ``include_raw`` is ``True``, returns a mapping instead of a list,
    where the key the brace-expression string and the value is the list of
    paths making up that particular brace-expression. (Which, with no
    expansion, will always be the same as the input list; with expansion it's
    usually a subset.)

    With expansions & include_raw, you'd get e.g. {"foo.bar": ["foo.bar"],
    "foo.biz": ["foo.biz"]} for the same input as above and an expansion list
    of [1]. Pretty tautological.

    A more complex example would be partial expansion. Calling
    combine(["a.1.b.1", "a.1.b.2", "a.2.b.1", "a.2.b.2"], expansions=[1],
    include_raw=True) would result in:

        {
            "a.{1,2}.b.1": ["a.1.b.1", "a.2.b.1"],
            "a.{1,2}.b.2": ["a.1.b.2", "a.2.b.2"]
        }

    because the first "overlapping" segment (a.1 vs a.2) is expanded, but the
    second (b.1 vs b.2) is not, and thus we get two keys whose values split the
    incoming 4-item list in half.
    """
    # Preserve input
    original_paths = paths[:]
    buckets = defaultdict(list)
    # Divvy up paths into per-segment buckets
    for path in paths:
        for i, part in enumerate(path.split('.')):
            if part not in buckets[i]:
                buckets[i].append(part)
    # "Zip" up buckets as needed depending on expansions
    ret = [[]]
    for key in sorted(buckets.keys()):
        value = list(buckets[key])
        # Only one value for this index: everybody gets a copy
        if len(value) == 1:
            for x in ret:
                x.append(value[0])
        else:
            # If this index is to be expanded, branch out: all existing results
            # up to this point get cloned, one per matching item
            if key in expansions:
                previous = ret[:]
                ret = []
                for x in value:
                    for y in previous:
                        ret.append(y + [x])
            # No expansion = just drop in the iterable, no conversion to string
            else:
                for x in ret:
                    x.append(value)
    # Now that we're done, merge the chains into strings
    mapping = {}
    # TODO: This is so dumb. Must be a way to merge with the nearly-identical
    # shit above.  I suck at algorithms.
    for expr in ret:
        key_parts = []
        paths = [[]]
        for part in expr:
            if isinstance(part, list):
                # Update paths
                previous = paths[:]
                paths = []
                for subpart in part:
                    for x in previous:
                        paths.append(x + [subpart])
                # Update key parts
                part = "{" + ",".join(part) + "}"
            else:
                for path in paths:
                    path.append(part)
            key_parts.append(part)
        # New final key/value pair
        # (Strip out any incorrectly expanded paths not present in the input.)
        # (TODO: figure out how not to expand combinatorically when that's not
        # correct. sigh)
        raw_paths = filter(
            lambda x: x in original_paths,
            map(lambda x: ".".join(x), paths)
        )
        # Do the same for keys, when expanding; have to search substrings.
        merged_path = ".".join(key_parts)
        merged_path_good = False
        lcd, _, rest = merged_path.partition('{')
        for original in original_paths:
            if original.startswith(lcd):
                merged_path_good = True
                break
        if merged_path_good:
            mapping[merged_path] = raw_paths
    return mapping if include_raw else mapping.keys()


class Metric(object):
    """
    Beefed-up metric object capable of substituting wildcards and more!
    """
    def __init__(
            self,
            path,
            config,
            excludes=(),
            expansions=(),
            title=None,
            title_param=None
        ):
        self.title = title or path
        self.title_param = title_param
        self.path = path
        self.config = config
        # Generate split version of our path, and note any wildcards
        self.parts = self.path.split('.')
        self.wildcards = self.find_wildcards()
        # Normalize/clean up options
        self.excludes = self.set_excludes(excludes)
        self.to_expand = self.set_expansions(expansions)

    def __repr__(self):
        return "<Metric %r, excluding %r, expanding %r>" % (
            self.path, self.excludes, self.to_expand
        )

    def __eq__(self, other):
        return (
            self.path == other.path
            and self.excludes == other.excludes
            and self.to_expand == other.to_expand
        )

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
        return map(func, self.config.graphite.query(path))

    def graphs(self, hostname=None, **kwargs):
        """
        Return 1+ Graph objects, optionally using ``hostname`` for context.

        Uses the initial ``excludes`` and ``expands`` options to determine
        which graphs to return. See ``metric.Metric.expand`` and
        ``metric.combine`` for details.

        Any kwargs passed in are passed into the Graph objects, so e.g.
        ``.graphs('foo.hostname', **{'from': '-24hours'})`` is a convenient way
        to get a collection of graphs for this metric all set to draw a 24 hour
        period.

        The kwargs will be used to override any defaults from the config
        object.
        """
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
        result = combine(matches, self.to_expand)
        merged_kwargs = dict(self.config.defaults, **kwargs)
        return [
            Graph(hostname, path, self.config, self.title, self.title_param, **merged_kwargs)
            for path in result
        ]
