#!/usr/bin/env python3
import json
import time

from tinydb import TinyDB, where
import requests
from tabulate import tabulate
import argparse
import logging
from PM3.model.process import Process, ProcessStatus, ProcessStatusLight
from rich import print
from pprint import pprint
from rich.table import Table
import os, signal
from pathlib import Path
from configparser import ConfigParser
import psutil
import asyncio
from pytailer import async_fail_tail

#logging.basicConfig(level=logging.DEBUG)

async def tailfile(proc):
    with async_fail_tail(proc.stdout, lines=10) as tail:
        async for line in tail:  # be careful: infinite loop!
            print(line, end='', flush=True)


def _setup():
    pm3_home_dir = Path('~/.pm3').expanduser()
    config_file = f'{pm3_home_dir}/config.ini'
    Path(pm3_home_dir).mkdir(mode=0o755, exist_ok=True)
    myself = psutil.Process(os.getpid()).as_dict()
    if 'environ' in myself:
        if virtualenv_path := myself['environ'].get('VIRTUAL_ENV'):
            exe = Path(virtualenv_path, 'bin/python').as_posix()
            cmd = Path(virtualenv_path, 'bin/pm3_backend').as_posix()
        else:
            exe = psutil.Process(os.getpid()).as_dict()['exe']
            if Path('/usr/bin/pm3_backend').is_file():
                cmd = Path('/usr/bin/pm3_backend').as_posix()
            else:
                cmd = '#pm3_backend not found'


    if not Path(config_file).is_file():
        config = ConfigParser()
        config['main_section'] = {
            'pm3_home_dir': pm3_home_dir,
            'pm3_db': f'{pm3_home_dir}/pm3_db.json',
            'pm3_db_process_table': 'pm3_procs',
            'backend_url': 'http://127.0.0.1:5000/',
            'backend_start_interpreter': exe,
            'backend_start_command': cmd,
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
        #out = tabulate([tuple(i.values()) for i in res], headers=res[0].keys())
        # TODO sorting by pm3_id
        out = _tabulate(res)
        return out
    else:
        return '[yellow]there is nothing to look at[/yellow]'

def _tabulate(data):
    if len(data) == 0:
        return '[yellow]there is nothing to look at[/yellow]'
    from rich.console import Console
    c = Console()

    table = Table(show_header=True, header_style="bold yellow")
    for h in data[0].keys():
        table.add_column(h)

    for r in data:
        items = []
        for k, v in r.items():
            if r['autorun'] is True and k == 'pid' and v == -1:
                items.append(f'[red]!!![/red]')
            elif r['autorun'] is False and k == 'pid' and v == -1:
                items.append(f'[gray]-[/gray]')
            else:
                items.append(c.render_str(str(v)))
        table.add_row(*items)
    return table

def _show_status(res, light=True):
    for proc in res:
        if light:
            p = ProcessStatusLight(**proc)
        else:
            p = ProcessStatus(**proc)
        print('')
        print(f'[cyan]### {p.pm3_name} ({p.pm3_id}) ###[/cyan]')
        for k, v in p.dict().items():
            if k == 'status' and v == 'zombie':
                print(f'  {k}=[bold italic yellow on red blink]{v}')
            else:
                print(f'  {k}={v}')

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
    parser_ls.add_argument('id_or_name', const='all', nargs='?', type=str, help='Start id or process name')
    parser_ls.add_argument('-l', '--long', action='store_true', help='Status Process')

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
    parser_new.add_argument('--nohup', dest='nohup', action='store_true', help='nohup')
    parser_new.add_argument('--autorun', dest='pm3_autorun', action='store_true', help='process autorun after reboot')
    parser_new.add_argument('--stdout', dest='pm3_stdout', help='std out')
    parser_new.add_argument('--stderr', dest='pm3_stderr', help='std err')

    parser_start = subparsers.add_parser('start', help='start a process by id or name')
    parser_start.add_argument('id_or_name', help='Start id or process name')

    parser_stop = subparsers.add_parser('stop', help='stop a process by id or name')
    parser_stop.add_argument('id_or_name', help='Stop id or process name')

    parser_restart = subparsers.add_parser('restart', help='restart a process by id or name')
    parser_restart.add_argument('id_or_name', help='Restart id or process name')

    parser_restart = subparsers.add_parser('reset', help='reset process counter for id or name')
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
                backend = Process(cmd=config['main_section'].get('backend_start_command'),
                                  interpreter=config['main_section'].get('backend_start_interpreter'),
                                  pm3_name='__backend__',
                                  pm3_id=0,
                                  shell=False,
                                  nohup=True,
                                  stdout=f'{pm3_home_dir}/__backend__.log',
                                  stderr=f'{pm3_home_dir}/__backend__.err')
                p = backend.run()
                time.sleep(2)
                res = _post('new', backend.dict())
                # TODO: BUG se il processo esiste in tabella esce un errore
                if res['err']:
                    print(res)
                else:
                    print('[green]process starting[/green]')


        if args.stop:
            if not res['err']:
                os.kill(msg['pid'], signal.SIGKILL)
                print(f"send kill sig to pid {msg['pid']}")
            else:
                print('process already stopped')
                #print(res)

        if args.status:
            #res = _get('status')
            #print(res)
            #print(ProcessStatus(**res))
            res = _get(f'pstatus/0')
            if res:
                _show_status(res, light=False)
                # pprint([ProcessStatus(**proc).dict() for proc in res][0])
            else:
                print('[yellow]there is nothing to look at[/yellow]')

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
        #res = _get(f'ls/{args.id_or_name}')
        if args.id_or_name is None:
            if ls := _ls():
                print(ls)
            else:
                print('[yellow]there is nothing to look at[/yellow]')
        else:
            res = _get(f'pstatus/{args.id_or_name}')
            if res:
                if args.long:
                    _show_status(res, light=False)
                else:
                    _show_status(res)
                #pprint([ProcessStatus(**proc).dict() for proc in res][0])
            else:
                print('[yellow]there is nothing to look at[/yellow]')

    elif args.subparser == 'new':
        p = Process(cmd=args.cmd,
                    cwd=args.cwd or Path.home().as_posix(),
                    pm3_name=args.pm3_name or '',
                    pm3_id=args.pm3_id or -1,
                    nohup=args.nohup,
                    shell=args.pm3_shell,
                    autorun=args.pm3_autorun,
                    stdout=args.pm3_stdout or '',
                    stderr=args.pm3_stderr or '')
        res = _post('new', p.dict())
        if res['err']:
            print(res)
        else:
            print(f"[green]{res['msg']}[/green]")

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

    elif args.subparser == 'restart':
        res = _get(f'stop/{args.id_or_name}')
        if res['err']:
            print(f"[red]{res['msg']}[/red]")
        else:
            res = _get(f'start/{args.id_or_name}')
            if res['err']:
                print(f"[red]{res['msg']}[/red]")
            else:
                print(f"[green]{res['msg']}[/green]")

    elif args.subparser == 'reset':
        res = _get(f'reset/{args.id_or_name}')
        if res['err']:
            print(f"[red]{res['msg']}[/red]")
        else:
            print(f"[green]{res['msg']}[/green]")

    #elif args.subparser == 'log':
        #ion = find_id_or_name(tbl, args.id_or_name)
        #print(ion)
        #if len(ion.proc) == 1:
        #    asyncio.run(tailfile(ion.proc[0]))

    else:
        print(parser.format_help())

if __name__ == '__main__':
    main()