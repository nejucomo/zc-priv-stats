import decimal
from zc_priv_stats.numconv import dec2int


class DictAttrs (object):
    @staticmethod
    def wrap(thing, path):
        if type(thing) is dict:
            return DictAttrs(thing, path)
        elif type(thing) is list:
            return [
                DictAttrs.wrap(x, '{}[{}]'.format(path, i))
                for (i, x)
                in enumerate(thing)
            ]
        elif type(thing) is unicode:
            return thing.encode('utf8')
        elif type(thing) is decimal.Decimal:
            try:
                return dec2int(thing)
            except decimal.Inexact:
                return thing
        else:
            return thing

    def __init__(self, d, path):
        assert type(d) is dict, (d, path)
        self._d = d
        self._path = path

    def __repr__(self):
        return '<DictAddrs {} {!r}>'.format(self._path, self._d)

    def __getattr__(self, name):
        try:
            thing = self._d[name]
        except KeyError as e:
            e.args += (self,)
            raise

        return DictAttrs.wrap(thing, '{}.{}'.format(self._path, name))
