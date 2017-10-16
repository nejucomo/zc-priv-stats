import sys
import argparse
from decimal import Decimal
from pathlib2 import Path
from zc_priv_stats.chainscanner import ChainScanner
from zc_priv_stats.db import TopRecDB
from zc_priv_stats.numconv import ZAT_PER_ZEC


def main(args=sys.argv[1:]):
    """Calculate top receiver addresses."""
    opts = parse_args(args)
    cs = ChainScanner(opts.DATADIR)
    db = TopRecDB(opts.STATSDIR)

    for block in cs.block_iter(1):
        for tx in map(cs.get_txinfo, block.tx):
            for txo in tx.vout:
                try:
                    [address] = txo.scriptPubKey.addresses
                except ValueError as e:
                    e.args += (txo,)
                    raise

                db.table[address] += Decimal(txo.valueZat) / ZAT_PER_ZEC

        if block.height % 1000 == 0:
            db.write_table(block.height)


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
