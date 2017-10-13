import sys
import csv
import argparse
import decimal
from pathlib2 import Path
from zcli import zcashcli


ZAT_PER_ZEC = 100000000


def main(args=sys.argv[1:]):
    """
    Calculate privacy statistics in the Zcash blockchain.
    """
    opts = parse_args(args)
    cli = zcashcli.ZcashCLI(opts.DATADIR)
    db = CSVDBWriter(opts.STATSDIR, startheight=0)

    def get_txinfo(txid):
        return DictAttrs(cli.getrawtransaction(txid, 1))

    def get_txin_value(txin):
        tx = get_txinfo(txin.txid)
        txout = tx.vout[txin.vout]
        return txout.valueZat

    monetarybase = 0
    for block in block_iter(cli):
        blockstats = CounterDict()

        if block.height > 0:
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

        db.append_row(
            height=block.height,
            hash=block.hash,
            monetary_base=monetarybase,
            **blockstats
        )


def parse_args(args):
    p = argparse.ArgumentParser(description=main.__doc__)

    p.add_argument(
        '--datadir',
        dest='DATADIR',
        type=Path,
        default=Path.home() / '.zcash',
        help='Node datadir.',
    )

    p.add_argument(
        '--statsdir',
        dest='STATSDIR',
        type=Path,
        default=Path.home() / 'zc-priv-stats',
        help='Stats db dir.',
    )

    return p.parse_args(args)


def block_iter(cli):
    bhash = cli.getblockhash(0)
    while bhash is not None:
        block = DictAttrs.wrap(cli.getblock(bhash))
        yield block
        bhash = block.nextblockhash


def calculate_coinbase(
        height,
        halvinginterval=840000,
        slowstartinterval=20000,
        basesubsidy=1250000000,
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


def dec2int(d):
    """Convert a decimal to an integer exactly, raise Exception otherwise."""
    ctx = decimal.Context(traps=[decimal.Inexact])
    return int(ctx.to_integral_exact(d))


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
            return dec2int(thing)
        else:
            return thing

    def __init__(self, d):
        self._d = d

    def __repr__(self):
        return '<DictAddrs {!r}>'.format(self._d)

    def __getattr__(self, name):
        return DictAttrs.wrap(self._d[name])


class CounterDict (dict):
    def __getitem__(self, key):
        return self.get(key, 0)

    def __setitem__(self, key, value):
        assert type(value) is int, (key, value)
        if value == 0:
            self.pop(key, None)
        else:
            dict.__setitem__(self, key, value)


class CSVDBWriter (object):
    FIELDS = [
        'height',
        'hash',
        'tx-fully-shielded',
        'tx-truly-mixed',
        'tx-shielding',
        'tx-unshielding',
        'tx-transparent',
        'js-count',
        'coinbase',
        'monetary-base',
    ]

    def __init__(self, dbdir, startheight):
        assert startheight == 0, startheight
        self._dbdir = dbdir
        self._height = startheight
        self._writer = None

    def append_row(self, **fields):
        height = fields['height']
        assert self._height == height, (self._height, height)

        if self._is_boundary(height):
            self._open_writer()

        self._writer.writerow(
            dict([
                (k.replace('_', '-'), v)
                for (k, v)
                in fields.iteritems()
            ]),
        )
        self._height += 1

    # Private:
    _ROWS_PER_FILE = 1000

    def _open_writer(self):
        assert self._is_boundary(self._height)

        if self._writer is not None:
            self._writer.close()

        path = self._dbdir / 'db{:08}.csv'.format(self._height)
        self._writer = CSVDictWriterCloser(
            MultWriter(
                path.open('wb'),
                sys.stdout,
            ),
            self.FIELDS,
        )

    @classmethod
    def _is_boundary(cls, height):
        return height % cls._ROWS_PER_FILE == 0


class CSVDictWriterCloser (csv.DictWriter):
    def __init__(self, f, fieldnames):
        self._f = f
        csv.DictWriter.__init__(self, f, fieldnames, restval=0)
        self.writeheader()

    def close(self):
        self._f.close()


class MultWriter (object):
    def __init__(self, *fs):
        self._fs = fs

    def write(self, buf):
        for f in self._fs:
            f.write(buf)
            f.flush()

    def close(self):
        for f in self._fs:
            f.close()
