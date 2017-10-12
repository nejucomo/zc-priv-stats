import sys
import argparse
from pathlib2 import Path
from zcli import zcashcli


def main(args=sys.argv[1:]):
    """
    Calculate privacy statistics in the Zcash blockchain.
    """
    opts = parse_args(args)
    cli = zcashcli.ZcashCLI(opts.DATADIR)

    accstats = CounterDict()

    for block in block_iter(cli):
        blockstats = CounterDict()

        for txid in block.tx:
            txinfo = DictAttrs(cli.getrawtransaction(txid, 1))
            jscnt = len(txinfo.vjoinsplit)
            if jscnt > 0:
                blockstats['js-count'] += jscnt
                if len(txinfo.vin) == 0:
                    if len(txinfo.vout) == 0:
                        blockstats['tx-fully-shielded'] += 1
                    else:
                        blockstats['tx-unshielding'] += 1
                else:
                    if len(txinfo.vout) == 0:
                        blockstats['tx-shielding'] += 1
                    else:
                        blockstats['tx-truly-mixed'] += 1
            else:
                blockstats['tx-transparent'] += 1

        output = 'Block {0.height} {0.hash}'.format(block)
        for statname in [
                'tx-fully-shielded',
                'tx-truly-mixed',
                'tx-shielding',
                'tx-unshielding',
                'tx-transparent',
                'js-count',
        ]:
            output += '; {}={}'.format(statname, blockstats[statname])
        sys.stdout.write(output + '\n')

        for (k, v) in blockstats.iteritems():
            accstats[k] += v


def parse_args(args):
    p = argparse.ArgumentParser(description=main.__doc__)

    p.add_argument(
        '--datadir',
        dest='DATADIR',
        type=Path,
        default=Path.home() / '.zcash',
        help='Node datadir.',
    )

    return p.parse_args(args)


def block_iter(cli):
    bhash = cli.getblockhash(1)
    while bhash is not None:
        block = DictAttrs.wrap(cli.getblock(bhash))
        yield block
        bhash = block.nextblockhash


class DictAttrs (object):
    @staticmethod
    def wrap(thing):
        if type(thing) is dict:
            return DictAttrs(thing)
        elif type(thing) is list:
            return [DictAttrs.wrap(x) for x in thing]
        elif type(thing) is unicode:
            return thing.encode('utf8')
        else:
            return thing

    def __init__(self, d):
        self._d = d

    def __repr__(self):
        return '<DictAddrs {!r}>'.format(self._d.keys())

    def __getattr__(self, name):
        return DictAttrs.wrap(self._d[name])


class CounterDict (dict):
    def __getitem__(self, key):
        return self.get(key, 0)

    def __setitem__(self, key, value):
        if value == 0:
            self.pop(key, None)
        else:
            dict.__setitem__(self, key, value)
