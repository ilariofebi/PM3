import os
from PM3.model.pm3_protocol import ION
from PM3.model.process import Process
from tinydb import where
from tinydb.table import Table
import fcntl

def hidden_proc(x: str) -> bool:
    return x.startswith('__') and x.endswith('__')

from filelock import FileLock

class Pm3Table:
    def __init__(self, tbl: Table, lock_file: str):
        self.tbl = tbl
        self.lock_file_name = lock_file

    # def locked_function():
    #     def wrapper(func):
    #         def inner(self, *args, **kwargs):
    #             print("locking...")
    #             print("locked")
    #             with FileLock(self.lock_file):
    #                 print(f"Lock acquired. Running func {func}...")
    #                 output = func(self, *args, **kwargs)
    #                 print("unlocking...")
    #             print("unlocking")
    #             return output
    #         return inner
    #     return wrapper
    
    def next_id(self, start_from=None):
        if start_from:
            # Next Id start from specific id
            pm3_id = start_from
            while self.check_exist(pm3_id):
                pm3_id += 1
            return pm3_id
        else:
            with FileLock(self.lock_file_name): lst = self.tbl.all()
            if len(lst) > 0:
                return max([i['pm3_id'] for i in self.tbl.all()])+1
            else:
                return 1

    def check_exist(self, val, col='pm3_id'):
        with FileLock(self.lock_file_name): return self.tbl.contains(where(col) == val)

    def select(self, proc, col='pm3_id'):
        with FileLock(self.lock_file_name): return self.tbl.get(where(col) == proc.model_dump()[col])

    def delete(self, proc, col='pm3_id'):
        if self.select(proc, col):
            with FileLock(self.lock_file_name):
                self.tbl.remove(where(col) == proc.model_dump()[col])
                return True
        else:
            return False

    def update(self, proc, col='pm3_id'):
        if self.select(proc, col):
            with FileLock(self.lock_file_name):
                self.tbl.update(proc, where(col) == proc.model_dump()[col])
                return True
        else:
            return False

    def find_id_or_name(self, id_or_name, hidden=False) -> ION:
        if id_or_name == 'all':
            # Tutti (nascosti esclusi)
            with FileLock(self.lock_file_name):
                out = ION('special',
                        id_or_name,
                        [Process(**i) for i in self.tbl.all() if not hidden_proc(i['pm3_name'])]
                        )
                return out

        elif id_or_name == 'ALL':
            # Proprio tutti (compresi i nascosti)
            with FileLock(self.lock_file_name):
                out = ION('special', id_or_name, [Process(**i) for i in self.tbl.all()])
                return out
        elif id_or_name == 'hidden_only':
            # Solo i nascosti (nascosti esclusi)
            with FileLock(self.lock_file_name):
                out = ION('special',
                        id_or_name,
                        [Process(**i) for i in self.tbl.all() if hidden_proc(i['pm3_name'])]
                        )
                return out

        elif id_or_name == 'autorun_only':
            # Tutti gli autorun (compresi i sospesi)
            with FileLock(self.lock_file_name):
                out = ION('special',
                        id_or_name,
                        [Process(**i) for i in self.tbl.all() if i['autorun'] is True])
            return out
        elif id_or_name == 'autorun_enabled':
            # Gruppo di autorun non sospesi
            with FileLock(self.lock_file_name):
                out = ION('special',
                        id_or_name,
                        [Process(**i) for i in self.tbl.all() if i['autorun'] is True and i['autorun_exclude'] is False])
                return out

        try:
            id_or_name = int(id_or_name)
        except ValueError:
            if self.check_exist(id_or_name, col='pm3_name'):
                with FileLock(self.lock_file_name):
                    p_data = self.tbl.get(where('pm3_name') == id_or_name)
                out = ION('pm3_name', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_name', id_or_name, [])

        else:
            if self.check_exist(id_or_name, col='pm3_id'):
                with FileLock(self.lock_file_name):
                    p_data = self.tbl.get(where('pm3_id') == id_or_name)
                out = ION('pm3_id', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_id', id_or_name, [])
        return out
