from collections import defaultdict
from types import StringTypes


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
            if not isinstance(part, str):
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
        mapping[".".join(key_parts)] = map(lambda x: ".".join(x), paths)
    return mapping if include_raw else mapping.keys()


class DisplayMetric(object):
    def __init__(self, path, config):
        self.path = path
        self.config = config

    def __str__(self):
        return self.path

    def render_params(self, hostname, **overrides):
        """
        Returns GET param kwargs for rendering this metric on given hostname.

        Designed for use with a 'render' URL endpoint.

        Will filter the 'from' kwarg through config.periods first.  Also sets a
        default 'title' kwarg to metric + period/from.
        """
        # Merge with defaults from config
        kwargs = dict(self.config.defaults, **overrides)
        # Set a default (runtime) title
        if 'title' not in kwargs:
            kwargs['title'] = "%s (%s)" % (self, kwargs['from'])
        # Translate period names in 'from' kwarg if needed
        f = kwargs['from']
        kwargs['from'] = self.config.periods.get(f, f)
        kwargs['target'] = "%s.%s" % (hostname, self.path)
        return kwargs


class Metric(object):
    """
    Beefed-up metric object capable of substituting wildcards and more!
    """
    def __init__(self, path, config, excludes=(), expansions=()):
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

    def normalize(self, hostname=None):
        """
        Return a list of one or more sub-metrics based on our options.

        For example, a basic ``Metric("foo.*")`` with no options would
        normalize into simply ``["foo.*"]``. ``Metric("foo.*", {'exclude':
        [1,2]})`` would expand out, remove any matching exclusions, compress
        again, and return e.g. ``["foo.{3,4,5}]``. And ``Metric("foo.*",
        {'expand': 'true'})`` would cause full expansion, returning e.g.
        ``["foo.1", "foo.2", "foo.3", ...]``.

        These sub-metrics are represented as rich string-like objects.
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
        result = combine(matches, self.to_expand)
        return map(lambda x: DisplayMetric(x, self.config), result)

