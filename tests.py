from unittest import TestCase, main

import mock

import fullerene


def metrics(*args):
    def fake_metrics(pattern):
        return args
    def inner(func):
        return mock.patch('fullerene.metrics', fake_metrics)(func)
    return inner


class TestExpandMetrics(TestCase):
    @metrics("foo.1.bar", "foo.2.bar", "foo.3.bar")
    def test_implicit_exclude_list(self):
        metric = {
            "foo.*.bar": {
                "exclude": {0: ['1', '2']}
            }
        }
        result = fullerene.expand_metric(metric)
        assert result == ["foo.3.bar"]

    @metrics("foo.1.2", "foo.1.1", "foo.3.1")
    def test_implicit_exclude_list_applies_to_first_wildcard_only(self):
        metric = {
            "foo.*.*": {
                "exclude": ['1']
            }
        }
        result = fullerene.expand_metric(metric)
        assert result == ["foo.3.1"]

    @metrics("foo.1.bar", "foo.2.bar", "foo.3.bar")
    def test_explicit_exclude_list(self):
        metric = {
            "foo.*.bar": {
                "exclude": {
                    0: ['1', '2']
                }
            }
        }
        result = fullerene.expand_metric(metric)
        assert result == ["foo.3.bar"]

    @metrics(
        # Doesn't match any excludes
        "foo.2.bar.biz.baz",
        # Matches exclude in 1st wildcard slot
        "foo.1.2.3.4",
        # Matches exclude in 3rd wildcard slot
        "foo.bar.biz.2.bar"
    )
    def test_explicit_exclude_list_multiple_wildcards(self):
        metric = {
            "foo.*.bar.*.*": {
                "exclude": {
                    0: ['1'],
                    2: ["bar"]
                }
            }
        }
        result = fullerene.expand_metric(metric)
        assert result == ["foo.2.bar.biz.baz"]

if __name__ == '__main__':
    main()
