import re
import csv
import time
from zc_priv_stats.fields import FIELDS
from zc_priv_stats.ctrdict import CounterDict


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
        if not self._dbdir.is_dir():
            print 'mkdir {!r}'.format(str(self._dbdir))
            self._dbdir.mkdir()

        dbfiles = _get_sorted_db_files(self._dbdir)

        for p in dbfiles[-2:]:
            print 'rm {!r}'.format(str(p))
            p.unlink()

        lastrow = CounterDict({'height': -1})
        if len(dbfiles) > 2:
            dbpath = dbfiles[-3]
            print 'Scanning {!r}'.format(str(dbpath))
            with dbpath.open('rb') as f:
                for row in csv.csv.DictReader(f, FIELDS):
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


# Private
class _CSVWriter (csv.DictWriter):
    _first_starttime = time.time()

    def __init__(self, f, fieldnames):
        self._f = f
        self._starttime = time.time()
        csv.DictWriter.__init__(self, f, fieldnames, restval=0)
        self.writeheader()

    def close(self):
        self._f.close()
        stoptime = time.time()
        print 'Wrote {!r} in {:.2f} seconds; total {:.2f}seconds'.format(
            self._f.name,
            stoptime - self._starttime,
            stoptime - self._first_starttime,
        )


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


def _get_sorted_db_files(dbdir):
    _FILENAME_RGX = re.compile(r'^db[0-9]{8}.csv$')

    return sorted([
        n
        for n
        in dbdir.iterdir()
        if _FILENAME_RGX.match(n.name)
    ])
