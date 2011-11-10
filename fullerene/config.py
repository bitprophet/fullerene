import yaml

from graphite import Graphite
from metric import Metric


class Config(object):
    def __init__(self, text):
        # Load up
        config = yaml.load(text)
        # Required items
        try:
            try:
                exclude_hosts = config['hosts']['exclude']
            except KeyError:
                exclude_hosts = []
            self.graphite = Graphite(
                uri=config['graphite_uris']['internal'],
                exclude_hosts=exclude_hosts
            )
        except KeyError:
            raise ValueError, "Configuration must specify graphite_uris: internal"
        # Optional external URL (for links)
        self.external_graphite = config['graphite_uris'].get('external', None)
        # 'metrics' section
        self.metrics = {}
        for name, options in config.get('metrics', {}).iteritems():
            self.metrics[name] = Metric(
                options=options,
                config=self
            )
        # Metric groups
        self.groups = {}
        for name, metrics in config.get('metric_groups', {}).iteritems():
            if name not in self.groups:
                self.groups[name] = {}
            for item in metrics:
                self.groups[name][item] = self.parse_metric(item)
        # 'collections'
        self.collections = config.get('collections', {})
        for collection in self.collections.values():
            for group in collection['groups'].values():
                group['metrics'] = map(self.parse_metric, group['metrics'])
        # Default graph args
        self.defaults = config.get('defaults', {})
        # Timeperiod aliases
        self.periods = config.get('periods', {})

    def parse_metric(self, item):
        # First check for any named metrics
        if item in self.metrics:
            metric = self.metrics[item]
        # Then create one on the fly
        else:
            metric = Metric({'path': item}, config=self)
        return metric

    @property
    def metric_groups(self):
        return sorted(self.groups)
