import sys
import argparse
from pathlib2 import Path
from zc_priv_stats.chainscanner import ChainScanner
from zc_priv_stats.ctrdict import CounterDict
from zc_priv_stats.db import DBWriter
from zc_priv_stats.numconv import zec2zat


def main(args=sys.argv[1:]):
    """
    Calculate privacy statistics in the Zcash blockchain.
    """
    opts = parse_args(args)
    cs = ChainScanner(opts.DATADIR)
    db = DBWriter(opts.STATSDIR)

    height = db.lastrow['height'] + 1
    print 'Starting at block height {!r}...'.format(height)

    monetarybase = db.lastrow['monetary-base']
    cumjscnt = db.lastrow['cumulative-js-count']
    mbshielded = db.lastrow['mb-shielded']

    for block in cs.block_iter(height):
        blockstats = CounterDict()

        if block.height > 0:
            for txinfo in map(cs.get_txinfo, block.tx):
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
