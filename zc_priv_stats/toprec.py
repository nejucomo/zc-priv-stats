import sys
import argparse
from decimal import Decimal
from pathlib2 import Path
from zc_priv_stats.chainscanner import ChainScanner
from zc_priv_stats.ctrdict import CounterDict
from zc_priv_stats.numconv import ZAT_PER_ZEC


def main(args=sys.argv[1:]):
    """Calculate top receiver addresses."""
    opts = parse_args(args)
    resultpath = opts.STATSDIR / 'toprec'
    cs = ChainScanner(opts.DATADIR)

    toprec = CounterDict()

    for block in cs.block_iter(1):
        for tx in map(cs.get_txinfo, block.tx):
            for txo in tx.vout:
                try:
                    [address] = txo.scriptPubKey.addresses
                except ValueError as e:
                    e.args += (txo,)
                    raise

                toprec[address] += txo.valueZat

        if block.height % 1000 == 0:
            print 'Writing info as of height {} to: {!r}'.format(
                block.height,
                str(resultpath),
            )
            with resultpath.open('wb') as f:
                f.write(
                    'As of height {}, top {} receivers:\n  {}\n'.format(
                        block.height,
                        len(toprec),
                        '\n  '.join([
                            '{}: {}'.format(
                                addr,
                                Decimal(value) / ZAT_PER_ZEC,
                            )
                            for (addr, value)
                            in sorted(
                                toprec.iteritems(),
                                key=lambda t: t[1],
                            )
                        ]),
                    ),
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
