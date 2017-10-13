import sys
import argparse
from decimal import Decimal
from pathlib2 import Path
from zcli import zcashcli


ZAT_PER_ZEC = Decimal('100000000')


def main(args=sys.argv[1:]):
    """
    Calculate privacy statistics in the Zcash blockchain.
    """
    opts = parse_args(args)
    cli = zcashcli.ZcashCLI(opts.DATADIR)

    def get_txinfo(txid):
        return DictAttrs(cli.getrawtransaction(txid, 1))

    def get_txin_value(txin):
        tx = get_txinfo(txin.txid)
        txout = tx.vout[txin.vout]
        return txout.valueZat / ZAT_PER_ZEC

    monetarybase = Decimal(0)
    for block in block_iter(cli):
        blockstats = CounterDict()

        for txinfo in map(get_txinfo, block.tx):
            # Coinbase:
            if 'coinbase' not in blockstats:
                coinbase = calculate_coinbase(block.height)
                blockstats['coinbase'] = coinbase
                monetarybase += coinbase

            jscnt = len(txinfo.vjoinsplit)
            blockstats['js-count'] += jscnt

            category = categorize_transaction(
                len(txinfo.vin),
                len(txinfo.vout),
                jscnt,
            )
            blockstats[category] += 1

        display_block_stats(block, blockstats, monetarybase)


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


def calculate_coinbase(
        height,
        halvinginterval=840000,
        slowstartinterval=20000,
        basesubsidy=Decimal('12.5'),
):
    if height < slowstartinterval / 2:
        return basesubsidy / slowstartinterval * height
    elif height < slowstartinterval:
        return basesubsidy / slowstartinterval * (height + 1)
    else:
        assert height > slowstartinterval
        halvings = (height - slowstartinterval / 2) / halvinginterval
        if halvings >= 64:
            return 0
        else:
            return basesubsidy >> halvings


def categorize_transaction(vins, vouts, jscnt):
    if jscnt > 0:
        if vins > 0:
            if vouts > 0:
                return 'tx-truly-mixed'
            else:
                return 'tx-shielding'
        else:
            if vouts > 0:
                return 'tx-unshielding'
            else:
                return 'tx-fully-shielded'
    else:
        return 'tx-transparent'


def display_block_stats(block, blockstats, monetarybase):
    output = 'Block {0.height} {0.hash}'.format(block)
    for statname in [
            'tx-fully-shielded',
            'tx-truly-mixed',
            'tx-shielding',
            'tx-unshielding',
            'tx-transparent',
            'js-count',
            'coinbase',
    ]:
        output += '; {}={}'.format(statname, blockstats[statname])
    output += '; monetary-base={}'.format(monetarybase)
    sys.stdout.write(output + '\n')


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
        assert type(value) in (int, Decimal), (key, value)
        if value == 0:
            self.pop(key, None)
        else:
            dict.__setitem__(self, key, value)
