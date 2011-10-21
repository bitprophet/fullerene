import os.path

import mock
from nose.tools import eq_, raises
from nose.plugins.skip import SkipTest

from metric import Metric, combine
from config import Config


def conf(name):
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "support", name + ".yml")) as fd:
        return fd.read()


class TestMetrics(object):
    def test_exclusions(self):
        config = Config(conf("exclusions"))
        for desc, name, expansions, result in (
            ("Implicit exclude list",
                "implicit",
                ("foo.1.bar", "foo.2.bar", "foo.3.bar"),
                "foo.3.bar"
            ),
            ("Implicit exclude list applied only to 1st wildcard",
                "implicit_1st",
                ("foo.1.2", "foo.1.1", "foo.3.1"),
                "foo.3.1"
            ),
            ("Explicit exclude list",
                "explicit",
                ("foo.1.bar", "foo.2.bar", "foo.3.bar"),
                "foo.3.bar"
            ),
            ("Explicit exclude list, multiple wildcards",
                "explicit_multiple",
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
            with mock.patch.object(config, 'graphite', graphite):
                eq_.description = desc
                yield eq_, config.metrics[name].normalize(), [result]
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


def cmp_metrics(dict1, dict2):
    for metricname, metric in dict1.items():
        eq_(dict2[metricname], metric)


class TestConfig(object):
    @raises(ValueError)
    def test_required_options(self):
        """
        Config files must specify graphite_uri
        """
        Config(conf("no_url"))

    def test_graphite_uri(self):
        """
        Graphite URI access: config_obj.graphite.uri
        """
        eq_(Config(conf("basic")).graphite.uri, "whatever")

    def test_metrics(self):
        """
        A metrics struct should turn into a dict of Metrics
        """
        metric1 = Metric("foo.bar", mock.Mock())
        metric2 = Metric("biz.baz", mock.Mock())
        metrics = {
            "metric1": metric1,
            "metric2": metric2
        }
        cmp_metrics(Config(conf("basic")).metrics, metrics)
        eq_(Config(conf("basic")).metrics, metrics)

    def test_groups(self):
        """
        A groups struct should turn into a dict of lists of Metrics
        """
        groups = {
            'group1': {
                "raw.path": Metric("raw.path", mock.Mock()),
                "metric1": Metric("foo.bar", mock.Mock())
            },
            'group2': {
                "metric1": Metric("foo.bar", mock.Mock())
            }
        }
        config = Config(conf("basic"))
        for name, metrics in config.groups.items():
            cmp_metrics(metrics, groups[name])

    def test_metric_aliases(self):
        """
        List items in groups collections should honor custom metric names
        """
        config = Config(conf("basic"))
        aliased_metric = config.groups['group1']['metric1']
        eq_(aliased_metric.path, "foo.bar")

    def test_default_graph_args(self):
        """
        A 'defaults' struct should be added as-is, as an attribute.
        """
        config = Config(conf("basic"))
        eq_(config.defaults, {"height": 250, "width": 400, "from": "-2hours"})

    def test_exclude_hosts(self):
        """
        config['hosts']['exclude'] should become config.graphite.exclude_hosts
        """
        config = Config(conf("basic"))
        eq_(config.graphite.exclude_hosts, ['a', 'b'])


if __name__ == '__main__':
    main()
