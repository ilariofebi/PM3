from flask import Flask, request
from tinydb import TinyDB, where
from model.process import Process
import logging
import json

db = TinyDB('/tmp/pm3_db.json')
tbl = db.table('pm3_procs')

#from flask_crontab import Crontab

app = Flask(__name__)
#crontab = Crontab(app)


@app.post("/new")
def new_process():
    logging.debug(request.json)
    P = Process(**request.json)

    P.pm3_id = P.pm3_id or len(tbl.all())+1

    P.pm3_name = P.pm3_name or P.cmd.split(" ")[0]
    P.pm3_name = P.pm3_name.replace(' ','_')
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
    #return P.json()

@app.get("/rm/<id_or_name>")
def rm_process(id_or_name):
    print(id_or_name)
    if id_or_name == 'all':
        tbl.truncate()
        msg = 'All processes removed'
        return {'msg': msg, 'err': False}
    try:
        id_or_name = int(id_or_name)
        if tbl.contains(where('pm3_id') == id_or_name):
            p_data = tbl.get(where('pm3_id') == id_or_name)
            P = Process(**p_data)
            if P.is_running:
                P.stop()
            tbl.remove(where('pm3_id') == id_or_name)
            msg = f'process ID {id_or_name} removed'
            return {'msg': msg, 'err': False}
        else:
            msg = f'process ID {id_or_name} not found'
            return {'msg': msg, 'err': True}
    except ValueError:
        tbl.remove(where('pm3_id') == id_or_name)
        if tbl.contains(where('pm3_name') == id_or_name):
            tbl.remove(where('pm3_name') == id_or_name)
            msg = f'process name {id_or_name} removed'
            return {'msg': msg, 'err': False}
        else:
            msg = f'process name {id_or_name} not found'
            return {'msg': msg, 'err': True}


@app.get("/ls")
def ls_process():
    return json.dumps(tbl.all())

@app.get("/start")
def start_process():
    # id or name
    args = {k: v for k, v in request.args.items()}
    print(args)
    return args


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
