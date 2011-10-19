from unittest import TestCase, main

import mock
import nose

import fullerene
from metric import Metric, combine


def metrics(*args):
    def fake_metrics(pattern):
        return args
    def inner(func):
        return mock.patch('fullerene.metrics', fake_metrics)(func)
    return inner


#class TestExpandMetrics(TestCase):
#    @metrics("foo.1.bar", "foo.2.bar", "foo.3.bar")
#    def test_implicit_exclude_list(self):
#        metric = {
#            "foo.*.bar": {
#                "exclude": {0: ['1', '2']}
#            }
#        }
#        result = fullerene.expand_metric(metric)
#        assert result == ["foo.3.bar"]
#
#    @metrics("foo.1.2", "foo.1.1", "foo.3.1")
#    def test_implicit_exclude_list_applies_to_first_wildcard_only(self):
#        metric = {
#            "foo.*.*": {
#                "exclude": ['1']
#            }
#        }
#        result = fullerene.expand_metric(metric)
#        assert result == ["foo.3.1"]
#
#    @metrics("foo.1.bar", "foo.2.bar", "foo.3.bar")
#    def test_explicit_exclude_list(self):
#        metric = {
#            "foo.*.bar": {
#                "exclude": {
#                    0: ['1', '2']
#                }
#            }
#        }
#        result = fullerene.expand_metric(metric)
#        assert result == ["foo.3.bar"]
#
#    @metrics(
#        # Doesn't match any excludes
#        "foo.2.bar.biz.baz",
#        # Matches exclude in 1st wildcard slot
#        "foo.1.2.3.4",
#        # Matches exclude in 3rd wildcard slot
#        "foo.bar.biz.2.bar"
#    )
#    def test_explicit_exclude_list_multiple_wildcards(self):
#        metric = {
#            "foo.*.bar.*.*": {
#                "exclude": {
#                    0: ['1'],
#                    2: ["bar"]
#                }
#            }
#        }
#        result = fullerene.expand_metric(metric)
#        assert result == ["foo.2.bar.biz.baz"]


class TestPaths(TestCase):
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
        result = combine(["foo.bar", "foo.biz"], expansions=[1])
        assert result == ["foo.bar", "foo.biz"]
        result = combine(["1.2", "3.4"], expansions=[0, 1])
        assert set(result) == set(["1.2", "3.4", "1.4", "3.2"])


if __name__ == '__main__':
    main()
