#!/usr/bin/env python3

import os, sys
import time

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
from PM3.libs.pm3table import Pm3Table

pm3_home_dir = os.path.expanduser('~/.pm3')
config_file = f'{pm3_home_dir}/config.ini'

if not os.path.isfile(config_file):
    print('config file not found')
    sys.exit(1)

config = ConfigParser()
config.read(config_file)

db = TinyDB(config['main_section'].get('pm3_db'))
tbl = db.table(config['main_section'].get('pm3_db_process_table'))
ptbl = Pm3Table(tbl)

#from flask_crontab import Crontab

app = Flask(__name__)
#crontab = Crontab(app)
ret_msg = namedtuple('RetMsg', 'msg, err')

process_running_list = {}


def _kill_process(proc):
    pid = proc.pid
    if not proc.is_running:
        msg = f'process {proc.pm3_name}(id={proc.pm3_id}) not running'
        # TODO: aggiungere warning o una severity level e rendere il ret message almeno una named tupla
        return {'msg': msg, 'err': False}
    else:
        if pid in process_running_list:
            process_running_list[pid].kill()
            process_running_list[pid].wait()

        if proc.is_running:
            if proc.kill():
                if not ptbl.update(proc):
                    msg = f'Error updating {proc}'
                    return {'msg': msg, 'err': True}
                else:
                    msg = f'process {proc.pm3_name}(id={proc.pm3_id}) with pid {pid} was killed'
                    return {'msg': msg, 'err': False}
        else:
            msg = f'process {proc.pm3_name}(id={proc.pm3_id}) with pid {pid} was killed'
            return {'msg': msg, 'err': False}

        time.sleep(2)
        if proc.is_running:
            msg = f"Sorry, I can't stop pid={pid} :("
            return {'msg': msg, 'err': True}
        else:
            msg = f'process {proc.pm3_name}(id={proc.pm3_id}) with pid {pid} was killed'
            return {'msg': msg, 'err': False}

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
    proc = Process(**request.json)

    proc.pm3_id = proc.pm3_id if proc.pm3_id != -1 else ptbl.next_id()

    if tbl.contains(where('pm3_name') == proc.pm3_name):
        proc.pm3_name = f'{proc.pm3_name}_{proc.pm3_id}'

    if tbl.contains(where('pm3_id') == proc.pm3_id):
        msg = f'ID {proc.pm3_id} processo esistente'
        logging.info(msg)
        return {'msg': msg, 'err': True}
    elif tbl.contains(where('pm3_name') == proc.pm3_name):
        msg = 'Nome processo esistente'
        logging.info(msg)
        return {'msg': msg, 'err': True}
    else:
        tbl.insert(proc.dict())
        msg = f'process {proc.pm3_name} with id={proc.pm3_id} was added'
        return {'msg': msg, 'err': False}

@app.get("/rm/<id_or_name>")
def rm_process(id_or_name):
    ion = ptbl.find_id_or_name(id_or_name)

    if len(ion.proc) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        return {'msg': msg, 'err': True}

    ok_list_pm3_id = []
    for proc in ion.proc:
        ret = _kill_process(proc)
        if ret['err']:
            return ret
        else:
            ok_list_pm3_id.append(proc.pm3_id)

        if not ptbl.delete(proc):
            msg = f'Error updating {proc}'
            return {'msg': msg, 'err': True}

    msg = f'process id: {[i for i in ok_list_pm3_id]} was removed'
    return {'msg': msg, 'err': False}

@app.get("/ls")
def ls_process():
    out = []
    for p in tbl.all():
        # Trick for update pid
        proc = Process(**p)
        proc.is_running
        out.append(proc.dict())
    return json.dumps(out)

@app.get("/pstatus/<id_or_name>")
def pstatus(id_or_name):
    out = []
    ion = ptbl.find_id_or_name(id_or_name)
    for proc in ion.proc:
        # Trick for update pid
        proc.is_running
        out.append(proc)
    #return json.dumps([psutil.Process(proc.pid).as_dict() for proc in out if proc.pid > 0])
    return json.dumps([{**proc.dict(), **psutil.Process(proc.pid).as_dict()} for proc in out if proc.pid > 0])

@app.get("/reset/<id_or_name>")
def reset(id_or_name):
    ion = ptbl.find_id_or_name(id_or_name)
    for proc in ion.proc:
        proc.reset()
        if not ptbl.update(proc):
            msg = f'Error updating {proc}'
            return {'msg': msg, 'err': True}

    msg = f'process {[i.pm3_id for i in ion.proc]} counter reset'
    return {'msg': msg, 'err': False}


@app.get("/start/<id_or_name>")
def start_process(id_or_name):
    ion = ptbl.find_id_or_name(id_or_name)
    if len(ion.proc) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        return {'msg': msg, 'err': True}

    for proc in ion.proc:
        if proc.is_running:
            msg = f'process {proc.pm3_name}(id={proc.pm3_id}) already running with pid {proc.pid}'
            return {'msg': msg, 'err': True}
        else:
            try:
                p = proc.run()
                process_running_list[proc.pid] = p
                if not ptbl.update(proc):
                    msg = f'Error updating {proc}'
                    return {'msg': msg, 'err': True}
            except FileNotFoundError as e:
                print(e)
                msg = f'File Not Found: {Path(proc.cwd,proc.cmd).as_posix()} ({ion.type}={ion.data})'
                return {'msg': msg, 'err': True}
            else:
                msg = f'process {proc.pm3_name}(id={proc.pm3_id}) started with pid {proc.pid}'
                return {'msg': msg, 'err': False}


    msg = f'Strange Error'
    return {'msg': msg, 'err': True}

@app.get("/stop/<id_or_name>")
def stop_process(id_or_name):
    ion = ptbl.find_id_or_name(id_or_name)
    if len(ion.proc) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        return {'msg': msg, 'err': True}

    ok_list_pm3_id = []
    for proc in ion.proc:
        ret = _kill_process(proc)
        if ret['err']:
            return ret
        else:
            ok_list_pm3_id.append(proc.pm3_id)
    msg = f'process id: {[i for i in ok_list_pm3_id]} was killed succesfully'
    return {'msg': msg, 'err': False}






#@crontab.job(minute="*")
#def watchdog():
#    print('cron')


def main():
    url = config['main_section'].get('backend_url')
    dsn = dsnparse.parse(url)

    app.run(debug=True, host=dsn.host, port=dsn.port)

if __name__ == '__main__':
    main()