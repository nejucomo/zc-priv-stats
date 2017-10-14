import sys
import argparse
from pathlib2 import Path
import matplotlib.pyplot as plt
import numpy as np
from zc_priv_stats.db import DBReader
from zc_priv_stats.fields import FIELDS
from zc_priv_stats.zec import ZAT_PER_ZEC


def main(args=sys.argv[1:]):
    opts = parse_args(args)
    plotsdir = opts.STATSDIR / 'plots'
    if not plotsdir.is_dir():
        print 'mkdir {!r}'.format(str(plotsdir))
        plotsdir.mkdir()

    data = dict((f, []) for f in FIELDS)
    for row in DBReader(opts.STATSDIR):
        for field in FIELDS:
            if field != 'hash':
                data[field].append(row[field])

    for field in FIELDS:
        data[field] = np.array(data[field])

    height = data['height']
    mb = data['monetary-base']
    mbshielded = data['mb-shielded']

    generate_plot(
        plotsdir,

        height,
        ('b', mb / ZAT_PER_ZEC),
        ('g', mbshielded / ZAT_PER_ZEC),

        xlabel='block',
        ylabel='ZEC',
        title='Monetary Base',
        grid=True,
    )

    generate_plot(
        plotsdir,

        height,
        ('g', [
            100.0*s/m if m > 0 else 0.0
            for (m, s)
            in zip(mb, mbshielded)
        ]),

        xlabel='block',
        ylabel='shielded monetary base %',
        title='Relative Shielded Monetary Base',
        grid=True,
    )

    generate_plot(
        plotsdir,

        height,
        ('g', [
            100.0*s/m if m > 0 else 0.0
            for (m, s)
            in zip(mb, mbshielded)
        ]),

        xlabel='block',
        ylabel='shielded monetary base %',
        title='Relative Shielded Monetary Base (feature zoom)',
        grid=True,
        axis=[30850, 30950, 0, 5],
    )

    generate_plot(
        plotsdir,

        height,
        ('g', data['mb-shielding'] / ZAT_PER_ZEC),
        ('r', -data['mb-unshielding'] / ZAT_PER_ZEC),

        xlabel='block',
        ylabel='ZEC',
        title='Shielding/Unshielding Volume',
        grid=True,
    )

    generate_plot(
        plotsdir,

        height,
        ('g.', data['mb-shielding'] / ZAT_PER_ZEC),
        ('r.', -data['mb-unshielding'] / ZAT_PER_ZEC),

        xlabel='block',
        ylabel='ZEC',
        title='Shielding/Unshielding Volume (feature zoom)',
        grid=True,
        axis=[30850, 30950, -8000, 2500],
    )

    txfields = zip('rgbpy', [txf for txf in FIELDS if txf.startswith('tx-')])
    generate_plot(
        plotsdir,

        height,

        xlabel='block',
        ylabel='Transactions',
        title='Transaction Rates',
        grid=True,

        *[(c, data[f]) for (c, f) in txfields]
    )

    txfieldsjs = [(c, f) for (c, f) in txfields if f != 'tx-transparent']
    generate_plot(
        plotsdir,

        height,

        xlabel='block',
        ylabel='Transactions',
        title='Transaction Rates w/ JS',
        grid=True,

        *[(c, data[f]) for (c, f) in txfieldsjs]
    )


def parse_args(args):
    p = argparse.ArgumentParser(description=main.__doc__)

    p.add_argument(
        '--statsdir',
        dest='STATSDIR',
        type=Path,
        default=Path.home() / 'zc-priv-stats',
        help='Stats db dir.',
    )

    return p.parse_args(args)


def generate_plot(plotdir, x, *ys, **attrs):
    title = attrs['title']
    print 'Plotting:', title

    plt.figure()

    plotargs = []
    for (style, ydata) in ys:
        plotargs.extend([x, ydata, style])
    plt.plot(*plotargs)

    for (attr, val) in attrs.iteritems():
        getattr(plt, attr)(val)

    plotpath = plotdir / (title.replace('/', ':') + '.png')
    plt.savefig(str(plotpath))
    plt.close()
