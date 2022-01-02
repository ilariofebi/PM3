#!/usr/bin/env python3

import os, sys
from flask import Flask, request
from tinydb import TinyDB, where
from PM3.model.process import Process
import logging
import json
from collections import namedtuple
from configparser import ConfigParser
import dsnparse
import psutil
from pathlib import Path
from PM3.libs.dbfuncs import next_id, find_id_or_name, update

pm3_home_dir = os.path.expanduser('~/.pm3')
config_file = f'{pm3_home_dir}/config.ini'

if not os.path.isfile(config_file):
    print('config file not found')
    sys.exit(1)

config = ConfigParser()
config.read(config_file)

db = TinyDB(config['main_section'].get('pm3_db'))
tbl = db.table(config['main_section'].get('pm3_db_process_table'))

#from flask_crontab import Crontab

app = Flask(__name__)
#crontab = Crontab(app)
ret_msg = namedtuple('RetMsg', 'msg, err')


@app.get("/ping")
def pong():
    msg = json.dumps({'pid': os.getpid()})
    return ret_msg(msg, False)._asdict()

@app.get("/status")
def status():
    ps = psutil.Process(os.getpid())
    return ps.as_dict()

@app.post("/new")
def new_process():
    logging.debug(request.json)
    P = Process(**request.json)

    P.pm3_id = P.pm3_id or next_id(tbl)

    #P.pm3_name = P.pm3_name or P.cmd.split(" ")[0]
    #P.pm3_name = P.pm3_name.replace(' ', '_').replace('./', '').replace('/', '')
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
    ion = find_id_or_name(tbl, id_or_name)

    # Kill process before remove
    for P in ion.P:
        P.kill()
        if not update(tbl, P):
            msg = f'Error updating {P}'
            return {'msg': msg, 'err': True}

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
    ion = find_id_or_name(tbl, id_or_name)
    if len(ion.P) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        return {'msg': msg, 'err': True}

    for P in ion.P:
        if P.is_running:
            msg = f'process {P.pm3_name}(id={P.pm3_id}) already running with pid {P.pid}'
            return {'msg': msg, 'err': True}
        else:
            try:
                P.run()
                if not update(tbl, P):
                    msg = f'Error updating {P}'
                    return {'msg': msg, 'err': True}
            except FileNotFoundError as e:
                print(e)
                msg = f'File Not Found: {Path(P.cwd,P.cmd).as_posix()} ({ion.type}={ion.data})'
                return {'msg': msg, 'err': True}
            else:
                msg = f'process {P.pm3_name}(id={P.pm3_id}) started with pid {P.pid}'
                return {'msg': msg, 'err': False}


    msg = f'Strange Error'
    return {'msg': msg, 'err': True}

@app.get("/stop/<id_or_name>")
def stop_process(id_or_name):
    ion = find_id_or_name(tbl, id_or_name)
    if len(ion.P) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        return {'msg': msg, 'err': True}

    for P in ion.P:
        pid = P.pid
        if not P.is_running:
            msg = f'process {P.pm3_name}(id={P.pm3_id}) not running'
            return {'msg': msg, 'err': True}
        else:
            P.kill()
            if not update(tbl, P):
                msg = f'Error updating {P}'
                return {'msg': msg, 'err': True}

            msg = f'process {P.pm3_name}(id={P.pm3_id}) with pid {pid} was killed'
            return {'msg': msg, 'err': False}


@app.get("/restart")
def restart_process():
    # id or name
    pass


#@crontab.job(minute="*")
#def watchdog():
#    print('cron')


def main():
    url = config['main_section'].get('backend_url')
    dsn = dsnparse.parse(url)

    app.run(debug=True, host=dsn.host, port=dsn.port)

if __name__ == '__main__':
    main()