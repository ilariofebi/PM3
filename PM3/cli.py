#!/usr/bin/env python3
import json
from tinydb import TinyDB, where
import requests
from tabulate import tabulate
import argparse
import logging
from PM3.model.process import Process, ProcessStatus
from rich import print
import os, signal
from pathlib import Path
from configparser import ConfigParser
from PM3.libs.dbfuncs import next_id, find_id_or_name

#logging.basicConfig(level=logging.DEBUG)

def _setup():
    pm3_home_dir = Path('~/.pm3').expanduser()
    config_file = f'{pm3_home_dir}/config.ini'
    Path(pm3_home_dir).mkdir(mode=0o755, exist_ok=True)
    if not Path(config_file).is_file():
        config = ConfigParser()
        config['main_section'] = {
            'pm3_home_dir': pm3_home_dir,
            'pm3_db': f'{pm3_home_dir}/pm3_db.json',
            'pm3_db_process_table': 'pm3_procs',
            'backend_url': 'http://127.0.0.1:5000/',
            'backend_start_interpreter': Path('~/vp39/bin/python3').expanduser(),
            'backend_start_command': '#',
        }
        with open(config_file, 'w') as output_file:
            config.write(output_file)

def _read_config():
    pm3_home_dir = Path('~/.pm3').expanduser()
    config_file = f'{pm3_home_dir}/config.ini'
    if not Path(config_file).is_file():
        _setup()
    config = ConfigParser()
    config.read(config_file)
    return config


def _get(path):
    config = _read_config()
    base_url = config['main_section'].get('backend_url')
    r = requests.get(f'{base_url}/{path}')
    if r.status_code == 200:
        return r.json()
    else:
        return {}

def _post(path, jdata):
    config = _read_config()
    base_url = config['main_section'].get('backend_url')
    r = requests.post(f'{base_url}/{path}', json=jdata)
    if r.status_code == 200:
        return r.json()
    else:
        return {}

def _ls():
    if res := _get('ls'):
        out = tabulate([tuple(i.values()) for i in res], headers=res[0].keys())
        return out
    else:
        print('Nessun processo inserito')

def _new_test():
    p = Process(cmd='./asd.py',
                pm3_name='processo 1',
                pm3_id=1,
                shell=True,
                stderr='err.err')
    if res := _post('new', p.dict()):
        return res

def _ping():
    try:
        res = _get('ping')
    except requests.exceptions.ConnectionError as e:
        res = {'err': True, 'msg': e}
    return res


def main():
    config = _read_config()
    db = TinyDB(config['main_section'].get('pm3_db'))
    tbl = db.table(config['main_section'].get('pm3_db_process_table'))
    pm3_home_dir = config['main_section'].get('pm3_home_dir')

    parser = argparse.ArgumentParser(prog='pm3', description='Like pm2 without node.js')
    subparsers = parser.add_subparsers(dest='subparser')

    parser_ls = subparsers.add_parser('ls', help='show process')

    parser_daemon = subparsers.add_parser('daemon', help='Daemon options')
    parser_daemon.add_argument('-s', '--start', action='store_true', help='Start daemon')
    parser_daemon.add_argument('-S', '--stop', action='store_true', help='Stop daemon')
    parser_daemon.add_argument('-t', '--status', action='store_true', help='Status Info')

    parser_ping = subparsers.add_parser('ping', help='Ensure pm3 daemon has been launched')
    parser_ping.add_argument('-v', '--verbose', action='store_true', help='verbose')

    parser_new = subparsers.add_parser('new', help='create a new process')
    parser_new.add_argument('cmd', help='linux command')
    parser_new.add_argument('--cwd', dest='cwd', help='cwd of executable file')
    parser_new.add_argument('-n', '--name', dest='pm3_name', help='name into pm3')
    parser_new.add_argument('-i', '--id', dest='pm3_id', help='id into pm3')
    parser_new.add_argument('--shell', dest='pm3_shell', action='store_true', help='process into shell or not')
    parser_new.add_argument('--autorun', dest='pm3_autorun', action='store_true', help='process autorun after reboot')
    parser_new.add_argument('--stdout', dest='pm3_stdout', help='std out')
    parser_new.add_argument('--stderr', dest='pm3_stderr', help='std err')

    parser_start = subparsers.add_parser('start', help='start a process by id or name')
    parser_start.add_argument('id_or_name', help='Start id or process name')

    parser_stop = subparsers.add_parser('stop', help='stop a process by id or name')
    parser_stop.add_argument('id_or_name', help='Stop id or process name')

    parser_restart = subparsers.add_parser('restart', help='restart a process by id or name')
    parser_restart.add_argument('id_or_name', help='Restart id or process name')

    parser_rm = subparsers.add_parser('rm', help='remove a process')
    parser_rm.add_argument('id_or_name', help='Remove id or process name')

    parser_rename = subparsers.add_parser('rename', help='rename a process')
    parser_rename.add_argument('id_or_name', help='Remove id or process name')
    parser_rename.add_argument('-n', '--name', dest='pm3_name', help='name into pm3', required=True)

    parser_log = subparsers.add_parser('log', help='show log for a process')
    parser_log.add_argument('id_or_name', help='Show Log for id or process name')

    parser_err = subparsers.add_parser('err', help='show log for a process')
    parser_err.add_argument('id_or_name', help='Show Errors for id or process name')

    args = parser.parse_args()
    kwargs = vars(args)
    logging.debug(kwargs)

    if args.subparser == 'daemon':
        res = _ping()
        if not res['err']:
            msg = json.loads(res['msg'])

        if args.start:
            if not res['err']:
                print(f"process running on pid {msg['pid']}")
            else:

                cmd = f"{config['main_section'].get('backend_start_interpreter')} {config['main_section'].get('backend_start_command')}"
                backend = Process(cmd=cmd,
                                  pm3_name='__backend__',
                                  pm3_id=0,
                                  shell=False,
                                  stdout=f'{pm3_home_dir}/__backend__.log',
                                  stderr=f'{pm3_home_dir}/__backend__.err')
                backend.run(detach=True)
                print(f"process starting")

        if args.stop:
            if not res['err']:
                os.kill(msg['pid'], signal.SIGKILL)
                print(f"send kill sig to pid {msg['pid']}")
            else:
                print('process already stopped')
                #print(res)

        if args.status:
            res = _get('status')
            #print(res)
            print(ProcessStatus(**res))

    elif args.subparser == 'ping':
        res = _ping()
        if res['err']:
            print('[red]ERROR[/red]')
            if args.verbose:
                print(res['msg'])
        else:
            print('[green]PONG![/green]')
            if args.verbose:
                print(res['msg'])

    elif args.subparser == 'ls':
        if ls := _ls():
            print(ls)
        else:
            print('---')

    elif args.subparser == 'new':
        pm3_id = args.pm3_id or next_id(tbl)
        ion = find_id_or_name(tbl, pm3_id)
        if len(ion.P) > 0:
            print(f'pm3_id={pm3_id} already used')
        else:
            p = Process(cmd=args.cmd,
                        cwd=args.cwd or Path.home().as_posix(),
                        pm3_name=args.pm3_name or '',
                        pm3_id=args.pm3_id or next_id(tbl),
                        shell=args.pm3_shell,
                        autorun=args.pm3_autorun,
                        stdout=args.pm3_stdout or '',
                        stderr=args.pm3_stderr or '')
            print(p)
            res = _post('new', p.dict())
            if res['err']:
                print(res)
            else:
                print('[green]OK[/green]')
            #print(_new_test())

    elif args.subparser == 'rm':
        res = _get(f'rm/{args.id_or_name}')
        if res['err']:
            print(f"[red]{res['msg']}[/red]")
        else:
            print(f"[green]{res['msg']}[/green]")

    elif args.subparser == 'start':
        res = _get(f'start/{args.id_or_name}')
        if res['err']:
            print(f"[red]{res['msg']}[/red]")
        else:
            print(f"[green]{res['msg']}[/green]")

    elif args.subparser == 'stop':
        res = _get(f'stop/{args.id_or_name}')
        if res['err']:
            print(f"[red]{res['msg']}[/red]")
        else:
            print(f"[green]{res['msg']}[/green]")

    else:
        print(parser.format_help())

if __name__ == '__main__':
    main()