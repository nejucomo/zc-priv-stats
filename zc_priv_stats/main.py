import sys
import re
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
    db = CSVDBWriter(opts.STATSDIR)

    def get_txinfo(txid):
        return DictAttrs(cli.getrawtransaction(txid, 1))

    def get_txin_value(txin):
        tx = get_txinfo(txin.txid)
        txout = tx.vout[txin.vout]
        return txout.valueZat

    monetarybase = db.lastrow['monetary-base']
    cumjscnt = db.lastrow['cumulative-js-count']
    mbshielded = db.lastrow['mb-shielded']
    for block in block_iter(cli, db.lastrow['height'] + 1):
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
                cumjscnt += jscnt

                for js in txinfo.vjoinsplit:
                    shielding = zec2zat(js.vpub_old)
                    unshielding = zec2zat(js.vpub_new)
                    blockstats['mb-shielding'] += shielding
                    blockstats['mb-unshielding'] += unshielding
                    mbshielded += shielding - unshielding

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
            cumulative_js_count=cumjscnt,
            mb_shielded=mbshielded,
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


def block_iter(cli, startheight):
    bhash = cli.getblockhash(startheight)
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
        assert height >= slowstartinterval
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


def zec2zat(d):
    """Convert a ZEC decimal to a ZAT integer."""
    return dec2int(d * ZAT_PER_ZEC)


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
        'cumulative-js-count',
        'coinbase',
        'monetary-base',
        'mb-shielded',
        'mb-shielding',
        'mb-unshielding',
    ]

    def __init__(self, dbdir):
        self._dbdir = dbdir
        self._writer = None
        self._refresh()

    def append_row(self, **fields):
        height = fields['height']
        if self._is_boundary(height):
            self._open_writer(height)

        row = dict([
            (k.replace('_', '-'), v)
            for (k, v)
            in fields.iteritems()
        ])
        self._writer.writerow(row)

    # Private:
    _ROWS_PER_FILE = 1000
    _FILENAME_RGX = re.compile(r'^db[0-9]{8}.csv$')

    def _refresh(self):
        """Refresh the database state to prepare for appending.

        Delete the last two db files, in case there was a
        chain-reorg. Then, if there are any db files, load the last row
        to retrieve accumulative values.
        """
        if not self._dbdir.is_dir():
            print 'mkdir {!r}'.format(self._dbdir)
            self._dbdir.mkdir()

        dbfiles = sorted([
            n
            for n
            in self._dbdir.iterdir()
            if self._FILENAME_RGX.match(n.name)
        ])
        for p in dbfiles[-2:]:
            print 'rm {!r}'.format(p)
            p.unlink()

        lastrow = CounterDict({'height': -1})
        if len(dbfiles) > 2:
            with dbfiles[-3].open('rb') as f:
                for row in csv.DictReader(f, self.FIELDS):
                    lastrow = row
            lastrow = CounterDict(
                (f, int(v) if f != 'hash' else v)
                for (f, v)
                in lastrow.iteritems()
            )

        self.lastrow = lastrow

    def _open_writer(self, height):
        if self._writer is not None:
            self._writer.close()

        path = self._dbdir / 'db{:08}.csv'.format(height)
        print 'Writing {!r}'.format(path)
        self._writer = CSVDictWriterCloser(path.open('wb'), self.FIELDS)

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


class TeeWriter (object):
    def __init__(self, f):
        self._f = f

    def write(self, buf):
        for f in [self._f, sys.stdout]:
            f.write(buf)
            f.flush()

    def close(self):
        self._f.close()
