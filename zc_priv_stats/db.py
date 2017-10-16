import re
import csv
from decimal import Decimal
from zc_priv_stats.fields import FIELDS
from zc_priv_stats.ctrdict import CounterDict
from zc_priv_stats.optimer import OperationTimer


class DBWriter (object):
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

    def _refresh(self):
        """Refresh the database state to prepare for appending.

        Delete the last two db files, in case there was a
        chain-reorg. Then, if there are any db files, load the last row
        to retrieve accumulative values.
        """
        dbpath = _refresh_dbdata(self._dbdir, _STATS_FILENAME_RGX)

        lastrow = CounterDict({'height': -1})
        if dbpath is not None:
            print 'Scanning {!r}'.format(str(dbpath))
            with dbpath.open('rb') as f:
                for row in _CSVReader(f):
                    lastrow = row
        self.lastrow = lastrow

    def _open_writer(self, height):
        if self._writer is not None:
            self._writer.close()

        path = self._dbdir / 'db-{:08}.csv'.format(height)
        self._writer = _CSVWriter(path.open('wb'), FIELDS)

    @classmethod
    def _is_boundary(cls, height):
        return height % cls._ROWS_PER_FILE == 0


class DBReader (object):
    def __init__(self, dbdir):
        self._dbpaths = _get_sorted_db_files(dbdir)

    def __iter__(self):
        for p in self._dbpaths:
            with p.open('rb') as f:
                for row in _CSVReader(f):
                    yield row


class TopRecDB (object):
    def __init__(self, dbdir):
        self.table = CounterDict()
        self._dbdir = dbdir
        self._optimer = OperationTimer()
        self._refresh()

    def write_table(self, height):
        path = self._dbdir / 'toprec-{:08}.tab'.format(height)
        with path.open('wb') as f:
            pairs = sorted(self.table.iteritems(), key=lambda t: t[1])
            for (addr, value) in pairs:
                f.write('{}: {}\n'.format(addr, value))
        print 'Wrote {!r}; {}'.format(str(path), self._optimer.tick())

    def _refresh(self):
        path = _refresh_dbdata(self._dbdir, _TOPREC_FILENAME_RGX)
        if path is not None:
            print 'Loading: {!r}'.format(str(path))
            with path.open('rb') as f:
                for line in f:
                    [addr, zectxt] = line.strip().split(': ')
                    self.table[addr] = Decimal(zectxt)
                self.startheight = int(str(path)[7:-4])


# Private
_STATS_FILENAME_RGX = re.compile(r'^db-[0-9]{8}.csv$')
_TOPREC_FILENAME_RGX = re.compile(r'^toprec-[0-9]{8}.tab$')


class _CSVWriter (csv.DictWriter):
    def __init__(self, f, fieldnames):
        self._f = f
        self._optimer = OperationTimer()
        csv.DictWriter.__init__(self, f, fieldnames, restval=0)
        self.writeheader()

    def close(self):
        self._f.close()
        print 'Wrote {!r}; {}'.format(self._f.name, self._optimer.tick())


class _CSVReader (csv.DictReader):
    def __init__(self, f):
        csv.DictReader.__init__(self, f, FIELDS)
        headers = csv.DictReader.next(self)
        for (field, header) in headers.iteritems():
            assert field == header, (field, header)

    def next(self):
        return dict(
            (f, int(v) if f != 'hash' else v)
            for (f, v)
            in csv.DictReader.next(self).iteritems()
        )


def _get_sorted_db_files(dbdir, filenamergx):
    return sorted([
        n
        for n
        in dbdir.iterdir()
        if filenamergx.match(n.name)
    ])


def _refresh_dbdata(dbdir, filenamergx):
    if not dbdir.is_dir():
        print 'mkdir {!r}'.format(str(dbdir))
        dbdir.mkdir()

    dbfiles = _get_sorted_db_files(dbdir, filenamergx)

    for p in dbfiles[-2:]:
        print 'rm {!r}'.format(str(p))
        p.unlink()

    if len(dbfiles) > 2:
        return dbfiles[-3]
    else:
        return None
