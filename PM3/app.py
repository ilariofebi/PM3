#!/usr/bin/env python3

import os, sys
import time

from flask import Flask, request
from tinydb import TinyDB, where
from PM3.model.process import Process
from PM3.model.pm3_protocol import RetMsg, KillMsg, alive_gone
import logging
from collections import namedtuple
from configparser import ConfigParser
import dsnparse
import psutil
from pathlib import Path
from PM3.libs.pm3table import Pm3Table, ION
import signal
import json
import threading

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

backend_process_name = config['backend'].get('name') or '__backend__'
cron_checker_process_name = config['cron_checker'].get('name') or '__cron_checker__'

app = Flask(__name__)


# Processi avviati localmente con popen:
# key = pid
# value = processo Popen
local_popen_process = {}

def _resp(res: RetMsg) -> dict:
    if res.err:
        logging.error(res.msg)
    if res.warn:
        logging.warning(res.msg)
    return res.dict()

def _insert_process(proc: Process, rewrite=False):
    proc.pm3_id = ptbl.next_id() if proc.pm3_id is None else proc.pm3_id

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

def _start_process(proc, ion) -> RetMsg:
    if proc.is_running:
        # Already running
        msg = f'process {proc.pm3_name} (id={proc.pm3_id}) already running with pid {proc.pid}'
        return RetMsg(msg=msg, warn=True)
    elif proc.restart >= proc.max_restart:
        # Max request exceded
        msg = f'ERROR, process {proc.pm3_name} (id={proc.pm3_id}) exceded max_restart {proc.restart}/{proc.max_restart}'
        return RetMsg(msg=msg, err=True)
    else:
        try:
            p = proc.run()
            local_popen_process[proc.pid] = p
            if not ptbl.update(proc):
                # Update Error
                msg = f'Error updating {proc}'
                return RetMsg(msg=msg, err=True)
        except FileNotFoundError as e:
            #print(e)
            # File not found
            msg = f'File Not Found: {Path(proc.cwd, proc.cmd).as_posix()} ({ion.type}={ion.data})'
            return RetMsg(msg=msg, err=True)
        else:
            # OK, process started
            msg = f'process {proc.pm3_name} (id={proc.pm3_id}) started with pid {proc.pid}'
            return RetMsg(msg=msg, err=False)



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


def _local_kill(proc):
    p = local_popen_process[proc.pid]
    local_pid = p.pid
    p.kill()
    for i in range(5):
        _ = p.poll()
        if not proc.is_running:
            break
        time.sleep(1)
    else:
        return KillMsg(msg='OK', alive=[alive_gone(pid=local_pid),], warn=True)
    # Elimino l'elemento dal dizionario
    _ = local_popen_process.pop(local_pid, None)
    return KillMsg(msg='OK', gone=[alive_gone(pid=local_pid), ])

def _interal_poll():
    for local_pid, p in local_popen_process.items():
        p.poll()

def _interal_poll_thread():
    # Interrogazione ciclica dei processi avviati da PM3
    # i processi contenuti in local_popen_process
    # vanno periodicamente interrogati
    while True:
        _interal_poll()
        time.sleep(1)

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
        if proc.pid in local_popen_process:
            # Processi attivati da os.getpid() vanno trattati con popen
            ret = _local_kill(proc)
        else:
            ret = proc.kill()

        if ret.msg == 'OK':
            proc.autorun_exclude = True
            ptbl.update(proc)
            for pk in ret.gone:
                msg = f'process {proc.pm3_name} (id={proc.pm3_id}) with pid {pk.pid} was killed'
                resp_list.append(_resp(RetMsg(msg=msg, err=False)))
        elif ret.warn:
            for pk in ret.alive:
                msg = f'process {proc.pm3_name} (id={proc.pm3_id}) with pid {pk.pid} still alive'
                resp_list.append(_resp(RetMsg(msg=msg, warn=True)))
            if ret.alive == 0:
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
        # Aggiorno lo stato dei processi
        _interal_poll()
        # Trick for update pid
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
        resp_list.append(_resp(_start_process(proc, ion)))
    return _resp(RetMsg(msg='', payload=resp_list))

def _make_fake_backend(pid, cwd):
    proc = Process(cmd=config['backend'].get('cmd'),
                   interpreter=config['main_section'].get('main_interpreter'),
                   pm3_name=backend_process_name,
                   pm3_id=0,
                   shell=False,
                   nohup=True,
                   stdout=f'{pm3_home_dir}/{backend_process_name}.log',
                   stderr=f'{pm3_home_dir}/{backend_process_name}.err',
                   pid=pid,
                   cwd=cwd,
                   restart=1,
                   max_restart=100000)
    return proc

def _make_cron_checker():
    proc = Process(cmd=config['cron_checker'].get('cmd'),
                   interpreter=config['main_section'].get('main_interpreter'),
                   pm3_name=cron_checker_process_name,
                   pm3_id=-1,
                   shell=False,
                   nohup=True,
                   stdout=f'{pm3_home_dir}/{cron_checker_process_name}.log',
                   stderr=f'{pm3_home_dir}/{cron_checker_process_name}.err',
                   max_restart=100000
                   )
    return proc


def main():
    my_pid = os.getpid()
    my_cwd = os.getcwd()
    url = config['backend'].get('url')
    dsn = dsnparse.parse(url)

    # __backend__ process
    ion_backend = ptbl.find_id_or_name(backend_process_name)
    if len(ion_backend.proc) == 0:
        # Se il processo non e' in lista lo credo in modo artificiale
        proc_backend = _make_fake_backend(my_pid, my_cwd)
        proc_backend.is_running
        _insert_process(proc_backend)
    else:
        proc_backend = ion_backend.proc[0]
        proc_backend.pid = my_pid
        proc_backend.cwd = my_cwd
        proc_backend.is_running
        ptbl.update(proc_backend)


    # __cron_checker__ process
    ion_cron = ptbl.find_id_or_name(cron_checker_process_name)
    if len(ion_cron.proc) == 0:
        proc_cron = _make_cron_checker()
        _insert_process(proc_cron)
    else:
        proc_cron = ion_cron.proc[0]

    ret_m = _resp(_start_process(proc_cron, ion_cron))
    if ret_m['err'] is True:
        print(ret_m)

    # Autorun
    ion = ptbl.find_id_or_name('autorun_enabled')
    for proc in ion.proc:
        proc.is_running
        ret_m = _resp(_start_process(proc, ion))
        if ret_m['err'] is True:
            print(ret_m)

    # Threads
    t1 = threading.Thread(target=_interal_poll_thread)
    t1.start()

    print(f'running on pid: {my_pid}')
    app.run(debug=True, host=dsn.host, port=dsn.port)

if __name__ == '__main__':
    main()
