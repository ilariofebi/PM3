import os
from time import sleep
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

        self.locked_all = self.locked_function(self.tbl.all)
        self.locked_contains = self.locked_function(self.tbl.contains)
        self.locked_get = self.locked_function(self.tbl.get)
        self.locked_remove = self.locked_function(self.tbl.remove)
        self.locked_update = self.locked_function(self.tbl.update)

    def locked_function(this, func):
        def inner(*args, **kwargs):
            print(f"locking for func  {func}...", flush=True)
            sleep(0.1)
            with FileLock(this.lock_file_name):
                print(f"> acquired lock...", flush=True)
                output = func(*args, **kwargs)
                #sleep(0.1)
                print("> unlocking...", flush=True)
            # sleep(0.1)
            print("unlocked", flush=True)
            return output
        return inner
    
    def next_id(self, start_from=None):
        if start_from:
            # Next Id start from specific id
            pm3_id = start_from
            while self.check_exist(pm3_id):
                pm3_id += 1
            return pm3_id
        else:
            all_docs = self.locked_all()
            if len(all_docs) > 0:
                return max([i['pm3_id'] for i in all_docs])+1
            else:
                return 1

    def check_exist(self, val, col='pm3_id'):
            return self.locked_contains(where(col) == val)

    def select(self, proc, col='pm3_id'):
        return self.locked_get(where(col) == proc.model_dump()[col])

    def delete(self, proc, col='pm3_id'):
        if self.select(proc, col):
            self.locked_remove(where(col) == proc.model_dump()[col])
            return True
        else:
            return False

    def update(self, proc, col='pm3_id'):
        if self.select(proc, col):
            self.locked_update(proc, where(col) == proc.model_dump()[col])
            return True
        else:
            return False

    def find_id_or_name(self, id_or_name, hidden=False) -> ION:
        if id_or_name == 'all':
            # Tutti (nascosti esclusi)
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if not hidden_proc(i['pm3_name'])]
                    )
            return out

        elif id_or_name == 'ALL':
            # Proprio tutti (compresi i nascosti)
            out = ION('special', id_or_name, [Process(**i) for i in self.locked_all()])
            return out
        elif id_or_name == 'hidden_only':
            # Solo i nascosti (nascosti esclusi)
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if hidden_proc(i['pm3_name'])]
                    )
            return out

        elif id_or_name == 'autorun_only':
            # Tutti gli autorun (compresi i sospesi)
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if i['autorun'] is True])
            return out
        elif id_or_name == 'autorun_enabled':
            # Gruppo di autorun non sospesi
            out = ION('special',
                    id_or_name,
                    [Process(**i) for i in self.locked_all() if i['autorun'] is True and i['autorun_exclude'] is False])
            return out

        try:
            id_or_name = int(id_or_name)
        except ValueError:
            if self.check_exist(id_or_name, col='pm3_name'):
                p_data = self.locked_get(where('pm3_name') == id_or_name)
                out = ION('pm3_name', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_name', id_or_name, [])

        else:
            if self.check_exist(id_or_name, col='pm3_id'):
                p_data = self.locked_get(where('pm3_id') == id_or_name)
                out = ION('pm3_id', id_or_name, [Process(**p_data), ])
            else:
                out = ION('pm3_id', id_or_name, [])
        return out
