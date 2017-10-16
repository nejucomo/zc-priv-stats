import decimal
from zc_priv_stats.numconv import dec2int


class DictAttrs (object):
    @staticmethod
    def wrap(thing):
        if type(thing) is dict:
            return DictAttrs(thing)
        elif type(thing) is list:
            return [DictAttrs.wrap(x) for x in thing]
        elif type(thing) is unicode:
            return thing.encode('utf8')
        elif type(thing) is decimal.Decimal:
            try:
                return dec2int(thing)
            except decimal.Inexact:
                return thing
        else:
            return thing

    def __init__(self, d):
        self._d = d

    def __repr__(self):
        return '<DictAddrs {!r}>'.format(self._d)

    def __getattr__(self, name):
        return DictAttrs.wrap(self._d[name])
