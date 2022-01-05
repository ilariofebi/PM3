from collections import namedtuple
from PM3.model.process import Process
from tinydb import where


class Pm3Table:
    def __init__(self, tbl):
        self.tbl = tbl

    def next_id(self, start_from=None):
        if start_from:
            # Next Id start from specific id
            pm3_id = start_from
            while self.check_exist(pm3_id):
                pm3_id += 1
            return pm3_id
        else:
            if len(self.tbl.all()) > 0:
                return max([i['pm3_id'] for i in self.tbl.all()])+1
            else:
                return 1

    def check_exist(self, val, col='pm3_id'):
        return self.tbl.contains(where(col) == val)

    def select(self, proc, col='pm3_id'):
        return self.tbl.get(where(col) == proc.dict()[col])

    def delete(self, proc, col='pm3_id'):
        if self.select(proc, col):
            self.tbl.remove(where(col) == proc.dict()[col])
            return True
        else:
            return False

    def update(self, proc, col='pm3_id'):
        if self.select(proc, col):
            self.tbl.update(proc, where(col) == proc.dict()[col])
            return True
        else:
            return False

    def find_id_or_name(self, id_or_name, hidden=False):
        ION = namedtuple('Id_or_Name', 'type, data, proc')

        if id_or_name == 'all':
            if hidden:
                out = ION('special', id_or_name, [Process(**i) for i in self.tbl.all()])
            else:
                out = ION('special',
                          id_or_name,
                          [Process(**i) for i in self.tbl.all() if i['pm3_name'] != '__backend__'])
            return out

        try:
            id_or_name = int(id_or_name)
        except ValueError:
            if self.check_exist(id_or_name, col='pm3_name'):
                p_data = self.tbl.get(where('pm3_name') == id_or_name)
                out = ION('pm3_name', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_name', id_or_name, [])

        else:
            if self.check_exist(id_or_name, col='pm3_id'):
                p_data = self.tbl.get(where('pm3_id') == id_or_name)
                out = ION('pm3_id', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_id', id_or_name, [])
        return out
