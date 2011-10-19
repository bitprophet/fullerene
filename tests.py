import mock
from nose.tools import eq_

from metric import Metric, combine


class TestMetrics(object):
    def test_exclusions(self):
        for desc, struct, expansions, result in (
            ("Implicit exclude list",
                {"foo.*.bar": {"exclude": {0: ['1', '2']}}},
                ("foo.1.bar", "foo.2.bar", "foo.3.bar"),
                "foo.3.bar"
            ),
            ("Implicit exclude list applied only to 1st wildcard",
                {"foo.*.*": {"exclude": ['1']}},
                ("foo.1.2", "foo.1.1", "foo.3.1"),
                "foo.3.1"
            ),
            ("Explicit exclude list",
                {"foo.*.bar": {"exclude": {0: ['1', '2']}}},
                ("foo.1.bar", "foo.2.bar", "foo.3.bar"),
                "foo.3.bar"
            ),
            ("Explicit exclude list, multiple wildcards",
                {"foo.*.bar.*.*": {"exclude": {0: ['1'], 2: ["bar"]}}},
                (
                    # Doesn't match any excludes
                    "foo.2.bar.biz.baz",
                    # Matches exclude in 1st wildcard slot
                    "foo.1.2.3.4",
                    # Matches exclude in 3rd wildcard slot
                    "foo.bar.biz.2.bar"
                ),
                "foo.2.bar.biz.baz"
            ),
        ):
            graphite = mock.Mock()
            graphite.query.return_value = expansions
            eq_.description = desc
            yield eq_, Metric(struct, graphite).normalize(), [result]
            del eq_.description

    def test_combinations(self):
        for desc, inputs, results in (
            ("Single metric, no combinations",
                ("foo.bar",), "foo.bar"),
            ("Single combination at end",
                ("foo.bar", "foo.biz"), "foo.{bar,biz}"),
            ("Combinations in both of two positions",
                ("foo.bar", "biz.baz"), "{foo,biz}.{bar,baz}"),
            ("One combination in the 2nd of 3 positions",
                ("foo.1.bar", "foo.2.bar"), "foo.{1,2}.bar"),
            ("Two combinations surrounding one normal part",
                ("foo.name.bar", "biz.name.baz"), "{foo,biz}.name.{bar,baz}"),
        ):
            eq_.description = desc
            yield eq_, combine(inputs), [results]
            del eq_.description

    def test_expansions(self):
        # Remember that expansion indexes apply only to wildcard slots,
        # which here are slots which differ from path to path and would thus
        # get combined by default.
        for desc, inputs, expansions, results in (
            ("Expand second part",
                ["foo.bar", "foo.biz"], [1], ["foo.bar", "foo.biz"]),
            ("Expand both parts",
                ["1.2", "3.4"], [0, 1], ["1.2", "3.4", "1.4", "3.2"]),
        ):
            eq_.description = desc
            yield eq_, set(combine(inputs, expansions)), set(results)
            del eq_.description


if __name__ == '__main__':
    main()
