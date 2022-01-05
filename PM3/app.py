#!/usr/bin/env python3

import os, sys
import time

from flask import Flask, request
from tinydb import TinyDB, where
from PM3.model.process import Process
from PM3.model.pm3_protocol import RetMsg
import logging
from collections import namedtuple
from configparser import ConfigParser
import dsnparse
import psutil
from pathlib import Path
from PM3.libs.pm3table import Pm3Table
import signal
import json

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

def _resp(res: RetMsg) -> dict:
    if res.err:
        logging.error(res.msg)
    if res.warn:
        logging.warning(res.msg)
    return res.dict()

def _insert_process(proc: Process, rewrite=False):
    proc.pm3_id = proc.pm3_id if proc.pm3_id != -1 else ptbl.next_id()

    if tbl.contains(where('pm3_name') == proc.pm3_name):
        if not rewrite:
            proc.pm3_name = f'{proc.pm3_name}_{proc.pm3_id}'

    if tbl.contains(where('pm3_id') == proc.pm3_id):
        if rewrite:
            tbl.remove(where('pm3_id') == proc.pm3_id)
            tbl.insert(proc.dict())
            return 'OK'
        return 'ID_ALREADY_EXIST'
    elif tbl.contains(where('pm3_name') == proc.pm3_name):
        return 'NAME_ALREADY_EXIST'
    else:
        tbl.insert(proc.dict())
        return 'OK'

def ps_proc_as_dict(ps_proc):
    '''
    Versione corretta di psutil.Process().as_dict()
    La versione originale non aggiorna i valori di CPU
    :param ps_proc:
    :return:
    '''
    ppad = ps_proc.as_dict()
    ppad['cpu_percent'] = ps_proc.cpu_percent(interval=0.1)
    return ppad


@app.get("/ping")
def pong():
    payload = {'pid': os.getpid()}
    return _resp(RetMsg(msg='PONG!', err=False, payload=payload))

@app.post("/new")
@app.post("/new/rewrite")
def new_process():
    logging.debug(request.json)
    proc = Process(**request.json)
    if 'rewrite' in request.path:
        ret = _insert_process(proc, rewrite=True)
    else:
        ret = _insert_process(proc)

    if ret == 'ID_ALREADY_EXIST':
        msg = f'process with id={proc.pm3_id} already exist'
        return _resp(RetMsg(msg=msg, warn=True))
    elif ret == 'NAME_ALREADY_EXIST':
        msg = f'process with name={proc.pm3_name} already exist'
        return _resp(RetMsg(msg=msg, err=True))
    elif ret == 'OK':
        msg = f'process [bold]{proc.pm3_name}[/bold] with id={proc.pm3_id} was added'
        return _resp(RetMsg(msg=msg, err=False))
    else:
        msg = f'Strange Error :('
        return _resp(RetMsg(msg=msg, err=True))


@app.get("/stop/<id_or_name>")
@app.get("/restart/<id_or_name>")
@app.get("/rm/<id_or_name>")
def stop_and_rm_process(id_or_name):
    resp_list = []
    ion = ptbl.find_id_or_name(id_or_name)
    if len(ion.proc) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        resp_list.append(_resp(RetMsg(msg=msg, err=True)))

    for proc in ion.proc:
        ret = proc.kill()
        if ret.msg == 'OK':
            ptbl.update(proc)
            for pk in ret.gone:
                msg = f'process {proc.pm3_name} (id={proc.pm3_id}) with pid {pk.pid} was killed'
                resp_list.append(_resp(RetMsg(msg=msg, err=False)))
            for pk in ret.alive:
                msg = f'process {proc.pm3_name} (id={proc.pm3_id}) with pid {pk.pid} still alive'
                resp_list.append(_resp(RetMsg(msg=msg, warn=True)))
        elif ret.warn:
            msg = f'process {proc.pm3_name} (id={proc.pm3_id}) not running'
            resp_list.append(_resp(RetMsg(msg=msg, warn=True)))
        else:
            msg = f'Strange Error'
            resp_list.append(_resp(RetMsg(msg=msg, warn=True)))

        if request.path.startswith('/rm/'):
            if not ptbl.delete(proc):
                msg = f'Error updating {proc}'
                resp_list.append(_resp(RetMsg(msg=msg, err=True)))
            else:
                msg = f'process {proc.pm3_name} (id={proc.pm3_id}) removed'
                resp_list.append(_resp(RetMsg(msg=msg, err=False)))

    if request.path.startswith('/restart/'):
        resp_list += start_process(id_or_name)['payload']

    return _resp(RetMsg(msg='', payload=resp_list))

@app.get("/ls/<id_or_name>")
def ls_process(id_or_name):
    payload = []
    ion = ptbl.find_id_or_name(id_or_name)
    for proc in ion.proc:
        # Trick for update pid
        if proc.pid in process_running_list:
            process_running_list[proc.pid].poll()
        proc.is_running
        ptbl.update(proc)
        payload.append(proc)
    return RetMsg(msg='OK', err=False, payload=payload).dict()

@app.get("/ps/<id_or_name>")
def pstatus(id_or_name):
    procs = []
    ion = ptbl.find_id_or_name(id_or_name)
    for proc in ion.proc:
        # Trick for update pid
        proc.is_running
        if id_or_name == 0 and proc.pid != os.getpid():
            proc.pid = os.getpid()
        ptbl.update(proc)  # Aggiorno anche il database
        procs.append(proc)

    payload = []
    for proc in procs:
        if proc.pid > 0:
            payload.append({**proc.dict(), **ps_proc_as_dict(psutil.Process(proc.pid))})

            # Children process
            for ps_proc in psutil.Process(proc.pid).children(recursive=True):
                payload.append({**proc.dict(), **ps_proc_as_dict(ps_proc)})

    return _resp(RetMsg(msg='OK', err=False, payload=payload))

@app.get("/reset/<id_or_name>")
def reset(id_or_name):
    resp_list = []
    ion = ptbl.find_id_or_name(id_or_name)
    for proc in ion.proc:
        proc.reset()
        if not ptbl.update(proc):
            msg = f'Error updating {proc}'
            resp_list.append(_resp(RetMsg(msg=msg, err=True)))
        else:
            msg = f'process {proc.pm3_name} (id={proc.pm3_id}) reset'
            resp_list.append(_resp(RetMsg(msg=msg, err=False)))
    return _resp(RetMsg(msg='', payload=resp_list))

@app.get("/start/<id_or_name>")
def start_process(id_or_name):
    resp_list = []
    ion = ptbl.find_id_or_name(id_or_name)
    if len(ion.proc) == 0:
        msg = f'process {ion.type}={ion.data} not found'
        resp_list.append(_resp(RetMsg(msg=msg, err=True)))

    for proc in ion.proc:
        if proc.is_running:
            msg = f'process {proc.pm3_name} (id={proc.pm3_id}) already running with pid {proc.pid}'
            resp_list.append(_resp(RetMsg(msg=msg, err=True)))
        else:
            try:
                p = proc.run()
                process_running_list[proc.pid] = p
                if not ptbl.update(proc):
                    msg = f'Error updating {proc}'
                    resp_list.append(_resp(RetMsg(msg=msg, err=True)))
            except FileNotFoundError as e:
                print(e)
                msg = f'File Not Found: {Path(proc.cwd,proc.cmd).as_posix()} ({ion.type}={ion.data})'
                resp_list.append(_resp(RetMsg(msg=msg, err=True)))
            else:
                msg = f'process {proc.pm3_name} (id={proc.pm3_id}) started with pid {proc.pid}'
                resp_list.append(_resp(RetMsg(msg=msg, err=False)))

    return _resp(RetMsg(msg='', payload=resp_list))


#@crontab.job(minute="*")
#def watchdog():
#    print('cron')

def main():
    url = config['main_section'].get('backend_url')
    dsn = dsnparse.parse(url)

    app.run(debug=True, host=dsn.host, port=dsn.port)

if __name__ == '__main__':
    main()
