from zcli import zcashcli
from zc_priv_stats.dictattrs import DictAttrs


class ChainScanner (object):
    def __init__(self, datadir):
        self._zcli = zcashcli.ZcashCLI(datadir)

    def block_iter(self, startheight):
        bhash = self._zcli.getblockhash(startheight)
        while bhash is not None:
            block = DictAttrs(
                self._zcli.getblock(bhash),
                '<block {!r}>'.format(bhash),
            )
            yield block
            bhash = block.nextblockhash

    def get_txinfo(self, txid):
        return DictAttrs(
            self._zcli.getrawtransaction(txid, 1),
            '<txn {!r}>'.format(txid),
        )

    def get_txin_value(self, txin):
        tx = self.get_txinfo(txin.txid)
        txout = tx.vout[txin.vout]
        return txout.valueZat
