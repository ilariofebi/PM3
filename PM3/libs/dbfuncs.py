from collections import namedtuple
from PM3.model.process import Process
from tinydb import TinyDB, where

def next_id(tbl):
    return len(tbl.all()) + 1

def find_id_or_name(tbl, id_or_name):
    ION = namedtuple('Id_or_Name', 'type, data, P')

    if id_or_name == 'all':
        out = ION('special', id_or_name, [Process(**i) for i in tbl.all()])
        return out

    try:
        id_or_name = int(id_or_name)
    except ValueError:
        if tbl.contains(where('pm3_name') == id_or_name):
            p_data = tbl.get(where('pm3_name') == id_or_name)
            out = ION('pm3_name', id_or_name, [Process(**p_data),])
        else:
            out = ION('pm3_name', id_or_name, [])

    else:
        if tbl.contains(where('pm3_id') == id_or_name):
            p_data = tbl.get(where('pm3_id') == id_or_name)
            out = ION('pm3_id', id_or_name, [Process(**p_data),])
        else:
            out = ION('pm3_id', id_or_name, [])
    return out

def update(tbl, P):
    p_data = tbl.get(where('pm3_id') == P.pm3_id)
    if p_data:
        tbl.update(P, where('pm3_id') == P.pm3_id)
        return True
    else:
        return False


