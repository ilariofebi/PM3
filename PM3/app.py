from flask import Flask, request
from tinydb import TinyDB, where
from model.process import Process
import logging
import json
from collections import namedtuple

db = TinyDB('/tmp/pm3_db.json')
tbl = db.table('pm3_procs')

#from flask_crontab import Crontab

app = Flask(__name__)
#crontab = Crontab(app)
ret_msg = namedtuple('RetMsg', 'msg, err')


def find_id_or_name(id_or_name):
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

@app.get("/ping")
def pong():
    return ret_msg('OK', False)._asdict()

@app.post("/new")
def new_process():
    logging.debug(request.json)
    P = Process(**request.json)

    P.pm3_id = P.pm3_id or len(tbl.all())+1

    P.pm3_name = P.pm3_name or P.cmd.split(" ")[0]
    P.pm3_name = P.pm3_name.replace(' ', '_').replace('./', '').replace('/', '')
    if tbl.contains(where('pm3_name') == P.pm3_name):
        P.pm3_name = f'{P.pm3_name}_{P.pm3_id}'

    if tbl.contains(where('pm3_id') == P.pm3_id):
        msg = 'ID processo esistente'
        logging.info(msg)
        return {'msg': msg, 'err': True}
    elif tbl.contains(where('pm3_name') == P.pm3_name):
        msg = 'Nome processo esistente'
        logging.info(msg)
        return {'msg': msg, 'err': True}
    else:
        tbl.insert(P.dict())
        msg = 'OK'
        return {'msg': msg, 'err': False}

@app.get("/rm/<id_or_name>")
def rm_process(id_or_name):
    ion = find_id_or_name(id_or_name)

    # Kill process before remove
    for p in ion.P:
        p.kill()

    if ion.type == 'special' and ion.data == 'all':
        tbl.truncate()
        msg = 'All processes removed'
        return {'msg': msg, 'err': False}

    if len(ion.P) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        return {'msg': msg, 'err': True}
    elif len(ion.P) == 1:
        tbl.remove(where(ion.type) == ion.data)
        msg = f'process {ion.type}={ion.data} removed'
        return {'msg': msg, 'err': False}

    else:
        msg = f'Strange Error 1 :-|'
        return {'msg': msg, 'err': True}



@app.get("/ls")
def ls_process():
    return json.dumps(tbl.all())

@app.get("/start/<id_or_name>")
def start_process(id_or_name):
    pass



@app.get("/stop")
def stop_process():
    # id or name
    args = {k: v for k, v in request.args.items()}
    print(args)
    return args


@app.get("/restart")
def restart_process():
    # id or name
    pass


#@crontab.job(minute="*")
#def watchdog():
#    print('cron')


if __name__ == '__main__':
    app.run(debug=True)
