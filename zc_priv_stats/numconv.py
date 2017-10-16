import decimal
from zc_priv_stats.zec import ZAT_PER_ZEC


def zec2zat(d):
    """Convert a ZEC decimal to a ZAT integer."""
    return dec2int(d * ZAT_PER_ZEC)


def dec2int(d):
    """Convert a decimal to an integer exactly, raise Exception otherwise."""
    ctx = decimal.Context(traps=[decimal.Inexact])
    return int(ctx.to_integral_exact(d))
