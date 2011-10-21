import yaml

from graphite import Graphite
from metric import Metric


class Config(object):
    def __init__(self, text):
        # Load up
        config = yaml.load(text)
        # Required items
        try:
            self.graphite = Graphite(uri=config['graphite_uri'])
        except KeyError:
            raise ValueError, "Configuration must specify graphite_uri"
        # 'metrics' section
        self.metrics = {}
        for name, options in config.get('metrics', {}).iteritems():
            self.metrics[name] = Metric(
                path=options['path'],
                config=self,
                excludes=options.get('exclude', ()),
                expansions=options.get('expand', ())
            )
        # 'groups' section
        self.groups = {}
        for name, metrics in config.get('groups', {}).iteritems():
            if name not in self.groups:
                self.groups[name] = {}
            for item in metrics:
                # First check for any named metrics
                if item in self.metrics:
                    new_metric = self.metrics[item]
                # Then create one on the fly
                else:
                    new_metric = Metric(path=item, config=self)
                self.groups[name][item] = new_metric
        # Default graph args
        self.defaults = config.get('defaults', {})
