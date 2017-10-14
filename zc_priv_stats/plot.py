import sys
import argparse
from pathlib2 import Path
import matplotlib.pyplot as plt
from zc_priv_stats.db import DBReader


def main(args=sys.argv[1:]):
    opts = parse_args(args)
    plotsdir = opts.STATSDIR / 'plots'
    if not plotsdir.is_dir():
        print 'mkdir {!r}'.format(str(plotsdir))
        plotsdir.mkdir()

    fields = ['height', 'monetary-base', 'mb-shielded']

    data = {}
    for field in fields:
        data[field] = []

    for row in DBReader(opts.STATSDIR):
        for field in fields:
            data[field].append(row[field])

    height = data['height']
    mb = data['monetary-base']
    mbshielded = data['mb-shielded']
    mbshieldedrel = [
        float(s)/m if m > 0 else 0.0
        for (m, s)
        in zip(mb, mbshielded)
    ]

    generate_plot(
        plotsdir,

        height,
        ('b', mb),
        ('g', mbshielded),

        xlabel='block',
        ylabel='monetary base',
        title='Monetary Base',
        grid=True,
    )

    generate_plot(
        plotsdir,

        height,
        ('g', mbshieldedrel),

        xlabel='block',
        ylabel='shielded monetary base',
        title='Relative Shielded Monetary Base',
        grid=True,
        # axis=[height[0], height[-1], 0, 1],
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
