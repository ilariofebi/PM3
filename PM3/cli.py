#!/usr/bin/env python3
import json
import sys
import time
import requests
import argparse, argcomplete
import logging
from PM3.model.process import Process, ProcessStatus, ProcessStatusLight, ProcessList
from PM3.model.pm3_protocol import RetMsg
from PM3.libs.system_scripts import pm3_scripts
from rich import print
from rich.table import Table
from rich.console import Console
import os, signal
from pathlib import Path
from configparser import ConfigParser
import psutil
import asyncio
from pytailer import async_fail_tail

#logging.basicConfig(level=logging.DEBUG)

async def tailfile(f, lines=10):
    with async_fail_tail(f, lines=lines) as tail:
        async for line in tail:  # be careful: infinite loop!
            print(line, end='', flush=True)

def _clean_ls_proc(p: dict) -> dict:
    p.pop('pid')
    p.pop('restart')
    p.pop('pm3_home')
    return p

def _setup():
    pm3_home_dir = Path('~/.pm3').expanduser()
    config_file = f'{pm3_home_dir}/config.ini'
    Path(pm3_home_dir).mkdir(mode=0o755, exist_ok=True)
    myself = psutil.Process(os.getpid()).as_dict()
    if 'environ' in myself:
        if virtualenv_path := myself['environ'].get('VIRTUAL_ENV'):
            exe = Path(virtualenv_path, 'bin/python').as_posix()
            cmd_backend = Path(virtualenv_path, 'bin/pm3_backend').as_posix()
            cmd_cron_checker = Path(virtualenv_path, 'bin/pm3_cron_checker').as_posix()
        else:
            exe = psutil.Process(os.getpid()).as_dict()['exe']

            if Path('/usr/bin/pm3_backend').is_file():
                cmd_backend = Path('/usr/bin/pm3_backend').as_posix()
            else:
                cmd_backend = '#pm3_backend not found'

            if Path('/usr/bin/pm3_cron_checker').is_file():
                cmd_cron_checker = Path('/usr/bin/pm3_cron_checker').as_posix()
            else:
                cmd_cron_checker = '#pm3_cron_checker not found'

    if not Path(config_file).is_file():
        config = ConfigParser()
        tcp_port = os.geteuid() + 6979
        config['main_section'] = {
            'pm3_home_dir': pm3_home_dir,
            'pm3_db': f'{pm3_home_dir}/pm3_db.json',
            'pm3_db_process_table': 'pm3_procs',
            'main_interpreter': exe,
        }
        config['backend'] = {
            'name': '__backend__',
            'cmd': cmd_backend,
            'url': f'http://127.0.0.1:{tcp_port}/',
        }
        config['cron_checker'] = {
            'name': '__cron_checker__',
            'cmd': cmd_cron_checker,
            'sleep_time': 5,
            'debug': False
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

def _make_script(filename, script, format_values=None, how_to_install=None, how_to_use=None, show_only=False):
    if format_values:
        script_text = pm3_scripts[script].format(**format_values)
    else:
        script_text = pm3_scripts[script]

    if show_only:
        print(f'[green]### {filename} ###[/green]')
        print('#'*80)
        print(script_text)
        print('#'*80)
    else:
        with open(filename, 'w') as f:
            f.write(script_text)
            print(f'file {filename} generated')

    if how_to_install:
        print('\n[yellow]HOW TO INSTALL:[/yellow]')
        print(how_to_install)
    if how_to_use:
        print('\n[yellow]HOW TO USE:[/yellow]')
        print(how_to_use)

def _get(path) -> RetMsg:
    config = _read_config()
    base_url = config['backend'].get('url')
    try:
        r = requests.get(f'{base_url}/{path}')
    except requests.exceptions.ConnectionError as e:
        return RetMsg(err=True, msg=str(e))

    if r.status_code == 200:
        ret = r.json()
        return RetMsg(**ret)
    else:
        return RetMsg(err=True, msg='Connection Error')

def _post(path, jdata):
    config = _read_config()
    base_url = config['backend'].get('url')
    try:
        r = requests.post(f'{base_url}/{path}', json=jdata)
    except requests.exceptions.ConnectionError:
        return RetMsg(err=True, msg='Connection Error')

    if r.status_code == 200:
        ret = r.json()
        return RetMsg(**ret)
    else:
        return RetMsg(err=True, msg='Connection Error')

def _parse_retmsg(res: RetMsg):
    if res.err:
        print(f"[red]{res.msg}[/red]")

    elif res.payload:
        for pi in res.payload:
            pi = RetMsg(**pi)
            if pi.err:
                print(f"[red]{pi.msg}[/red]")
            elif pi.warn:
                print(f"[yellow]{pi.msg}[/yellow]")
            else:
                print(f"[green]{pi.msg}[/green]")

    else:
        if res.warn:
            print(f"[yellow]{res.msg}[/yellow]")
        else:
            print(f"[green]{res.msg}[/green]")


def _ls(id_or_name='all', format='table'):
    res = _get(f'ls/{id_or_name}')
    if res.err:
        _parse_retmsg(res)
        return ''

    if res:
        payload_sorted = sorted(res.payload, key=lambda item: item.get("pm3_id"))
        if format == 'table':
            return _tabulate_ls(payload_sorted)
        else:
            return _show_list(payload_sorted)
    else:
        return '[yellow]there is nothing to look at[/yellow]'

def _ps(id_or_name='all', format='table'):
    res = _get(f'ps/{id_or_name}')
    if res.err:
        _parse_retmsg(res)
        return ''

    if not res.err:
        if res.payload:
            payload_sorted = sorted(res.payload, key=lambda item: item.get("pm3_id"))
            if format == 'table':
                return _tabulate_ps(payload_sorted)
            else:
                payload_sorted = [ProcessStatus(**p).dict() for p in payload_sorted]
                return _show_list(payload_sorted)
        else:
            return '[yellow]there is nothing to look at[/yellow]'
    else:
        return f'[red]{res.msg}[/red]'

def _show_list(data):
    out = []
    for row in data:
        out.append('')
        out.append(f"[cyan]### {row['pm3_name']} ({row['pm3_id']}) ###[/cyan]")
        for k, v in row.items():
            out.append(f'  {k}={v}')
    return '\n'.join(out)

def _tabulate_ps(data):
    if len(data) == 0:
        return '[yellow]there is nothing to look at[/yellow]'
    c = Console()

    table = Table(show_header=True, header_style="bold green")

    for n, r in enumerate(data):
        r = ProcessStatusLight(**r).dict()  # Validate and sort
        if n == 0:
            for h in r.keys():
                table.add_column(h)

        items = []
        for k, v in r.items():
            items.append(c.render_str(str(v)))
        table.add_row(*items)
    return table

def _tabulate_ls(data):
    if len(data) == 0:
        return '[yellow]there is nothing to look at[/yellow]'
    c = Console()

    table = Table(show_header=True, header_style="bold yellow")

    for n, r in enumerate(data):
        #r = Process(**r).dict()  # Validate and sort
        r = ProcessList(**r).dict()  # Validate and sort
        if n == 0:
            for h in r.keys():
                table.add_column(h)

        items = []
        for k, v in r.items():
            if 'autorun' in r and r['autorun'] is True and k == 'pid' and v == -1:
                items.append(f'[red]!!![/red]')
            elif 'autorun' in r and r['autorun'] is False and k == 'pid' and v == -1:
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


def main():
    config = _read_config()
    pm3_home_dir = config['main_section'].get('pm3_home_dir')
    backend_process_name = config['backend'].get('name') or '__backend__'
    cron_checker_process_name = config['cron_checker'].get('name') or '__cron_checker__'

    parser = argparse.ArgumentParser(prog='pm3', description='Like pm2 without node.js')
    subparsers = parser.add_subparsers(dest='subparser')

    parser_daemon = subparsers.add_parser('daemon', help='Daemon options')
    parser_daemon.add_argument('what', default='status', const='status', nargs='?',
                               choices=['start', 'stop', 'status'])

    parser_make_script = subparsers.add_parser('make_script', help='Make useful scripts')
    parser_make_script.add_argument('what', nargs='?', choices=['pm3_edit', 'systemd'])
    parser_make_script.add_argument('-s', '--show_only', action='store_true', help='Show only')

    parser_ping = subparsers.add_parser('ping', help='Ensure pm3 daemon has been launched')
    parser_ping.add_argument('-v', '--verbose', action='store_true', help='verbose')

    parser_ls = subparsers.add_parser('ls', help='process list')
    parser_ls.add_argument('id_or_name', const='all', nargs='?', type=str, help='id or process name')
    parser_ls.add_argument('-l', '--list', action='store_true', help='List format')

    parser_ps = subparsers.add_parser('ps', help='process status')
    parser_ps.add_argument('id_or_name', const='all', nargs='?', type=str, help='id or process name')
    parser_ps.add_argument('-l', '--list', action='store_true', help='List format')

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
    parser_new.add_argument('--interpreter', dest='interpreter', help='interpreter path')
    parser_new.add_argument('--max-restart', dest='max_restart', type=int, default=1000, help='maximal restart times')

    parser_start = subparsers.add_parser('start', help='start a process by id or name')
    parser_start.add_argument('id_or_name', help='id or process name')

    parser_stop = subparsers.add_parser('stop', help='stop a process by id or name')
    parser_stop.add_argument('id_or_name', help='id or process name')

    parser_restart = subparsers.add_parser('restart', help='restart a process by id or name')
    parser_restart.add_argument('id_or_name', help='id or process name')

    parser_restart = subparsers.add_parser('reset', help='reset process counter for id or name')
    parser_restart.add_argument('id_or_name', help='id or process name')

    parser_rm = subparsers.add_parser('rm', help='remove a process')
    parser_rm.add_argument('id_or_name', help='Remove id or process name')

    parser_rename = subparsers.add_parser('rename', help='rename a process')
    parser_rename.add_argument('id_or_name', help='id or process name')
    parser_rename.add_argument('-n', '--name', dest='pm3_name', help='name into pm3', required=True)

    parser_log = subparsers.add_parser('log', help='show log for a process')
    parser_log.add_argument('id_or_name', const='all', nargs='?', type=str, help='id or process name')
    parser_log.add_argument('-f', '--follow', action='store_true', help='tail follow')
    parser_log.add_argument('-n', '--lines', const=10, default=10, nargs='?', type=int, help='how many lines')

    parser_err = subparsers.add_parser('err', help='show log for a process')
    parser_err.add_argument('id_or_name', const='all', nargs='?', type=str, help='id or process name')
    parser_err.add_argument('-f', '--follow', action='store_true', help='tail follow')
    parser_err.add_argument('-n', '--lines', const=10, default=10, nargs='?', type=int, help='how many lines')

    parser_flush = subparsers.add_parser('flush', help='Flush logs')
    parser_flush.add_argument('id_or_name', help='id or process name')
    parser_flush.add_argument('what', nargs='?', choices=['log', 'err', 'all'])

    parser_dump = subparsers.add_parser('dump', help='dump process in file')
    parser_dump.add_argument('id_or_name', const='all', nargs='?', type=str, help='id or process name')
    parser_dump.add_argument('-f', '--file', dest='dump_file', help='dump into file', required=False)

    parser_load = subparsers.add_parser('load', help='load process from a file')
    parser_load.add_argument('-f', '--file', dest='load_file', help='load from this file', required=True)
    parser_load.add_argument('-r', '--rewrite', dest='load_rewrite', action='store_true', help='rewrite if process already exist')
    parser_load.add_argument('-y', '--yes', dest='load_yes', action='store_true', help='response always yes')

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    kwargs = vars(args)
    logging.debug(kwargs)

    if args.subparser == 'ping':
        res = _get('ping')
        if res.err:
            print('[red]ERROR[/red]')
            if args.verbose:
                print(res.msg)
        else:
            print('[green]PONG![/green]')
            if args.verbose:
                print(res.payload)

    elif args.subparser == 'daemon':
        res = _get('ping')
        if not res.err:
            msg = res.payload

        if args.what == 'start':
            if not res.err:
                print(f"process running on pid {msg['pid']}")
            else:
                backend = Process(cmd=config['backend'].get('cmd'),
                                  interpreter=config['main_section'].get('main_interpreter'),
                                  pm3_name=backend_process_name,
                                  pm3_id=0,
                                  shell=False,
                                  nohup=True,
                                  stdout=f'{pm3_home_dir}/{backend_process_name}.log',
                                  stderr=f'{pm3_home_dir}/{backend_process_name}.err')
                p = backend.run()
                time.sleep(2)
                if psutil.Process(p.pid).is_running():
                    res = _post('new/rewrite', backend.dict())
                    if res.err:
                        print(res)
                    else:
                        print('[green]process started[/green]')
                else:
                    print('[red]process NOT started[/red]')


        if args.what == 'stop':
            if not res.err:
                os.kill(msg['pid'], signal.SIGKILL)
                print(f"send kill sig to pid {msg['pid']}")
            else:
                print('process already stopped')
                #print(res)

        if args.what == 'status':
            # Presumo che i processi nascosti siano interessanti per lo status
            print(_ps('hidden_only', 'table'))

    elif args.subparser == 'make_script':
        if args.what == 'systemd':
            main_interpreter = config['main_section'].get('main_interpreter')
            backend_cmd = config['backend'].get('cmd')
            exec_start = f'{main_interpreter} {backend_cmd}' if main_interpreter else backend_cmd
            format_values = {
                'USER': os.getlogin(),
                'EXE': exec_start,
            }
            filename = 'systemd.sh'
            how_to_install = 'sudo bash systemd.sh'
            _make_script(filename,
                         'systemd',
                         format_values=format_values,
                         how_to_install=how_to_install,
                         show_only=args.show_only)

        elif args.what == 'pm3_edit':
            filename = 'pm3_edit.sh'
            how_to_install = f'chmod 755 {filename}'
            hot_to_use = f'./{filename} <id_or_name>'
            _make_script(filename,
                         'pm3_edit',
                         how_to_install=how_to_install,
                         how_to_use=hot_to_use,
                         show_only=args.show_only)

    elif args.subparser == 'ls':
        id_or_name = args.id_or_name or 'all'
        format_ = 'list' if args.list else 'table'
        print(_ls(id_or_name, format_))

    elif args.subparser == 'ps':
        id_or_name = args.id_or_name or 'all'
        format_ = 'list' if args.list else 'table'
        print(_ps(id_or_name, format_))

    elif args.subparser == 'new':
        p = Process(cmd=args.cmd,
                    cwd=args.cwd or Path.home().as_posix(),
                    pm3_name=args.pm3_name or '',
                    pm3_id=args.pm3_id or None,
                    interpreter=args.interpreter or '',
                    nohup=args.nohup,
                    shell=args.pm3_shell,
                    autorun=args.pm3_autorun,
                    stdout=args.pm3_stdout or '',
                    stderr=args.pm3_stderr or '',
                    max_restart=args.max_restart)
        res = _post('new', p.dict())
        if res.err:
            print(res)
        else:
            print(_ls('all', 'table'))
            print(f"[green]{res.msg}[/green]")
            print('')

    elif args.subparser == 'rm':
        res = _get(f'rm/{args.id_or_name}')
        _parse_retmsg(res)

    elif args.subparser == 'start':
        res = _get(f'start/{args.id_or_name}')
        _parse_retmsg(res)

    elif args.subparser == 'stop':
        res = _get(f'stop/{args.id_or_name}')
        _parse_retmsg(res)

    elif args.subparser == 'restart':
        res = _get(f'restart/{args.id_or_name}')
        _parse_retmsg(res)

    elif args.subparser == 'reset':
        res = _get(f'reset/{args.id_or_name}')
        _parse_retmsg(res)

    elif args.subparser in ('log', 'err'):
        res = _get(f"ls/{args.id_or_name or 'all'}")
        if res and not res.err:
            for p in res.payload:
                ftt = p['stdout'] if args.subparser == 'log' else p['stderr']
                print()

                if not Path(ftt).is_file():
                    print(f"[yellow] !!! file {ftt} don't exist !!! [/yellow]")
                    continue

                print(f"[yellow2] #### {ftt} #### [/yellow2]")

                try:
                    if args.follow:
                        asyncio.run(tailfile(ftt, lines=args.lines))
                    else:
                        with open(ftt, "r") as f1:
                            last_line = f1.readlines()[-args.lines:]
                            for r in last_line:
                                print(r, end='')
                except KeyboardInterrupt:
                    #print('CTRL+C')
                    pass

    elif args.subparser == 'flush':
        res = _get(f"ls/{args.id_or_name}")
        if args.what is None:
            print(parser_flush.format_help())
        else:
            arg_map = dict(
                err=['stderr'],
                log=['stdout'],
                all=['stdout', 'stderr'],
            )
            if res and not res.err:
                for p in res.payload:
                    for std in arg_map[args.what]:
                        ftt = p[std]

                        if not Path(ftt).is_file():
                            print(f"[yellow] !!! file {ftt} don't exist !!! [/yellow]")
                            continue
                        else:
                            open(Path(ftt), 'w').close()
                            print(f"[yellow2] {ftt} is emptied [/yellow2]")


    elif args.subparser == 'dump':
        res = _get(f"ls/{args.id_or_name or 'all'}")

        if res and not res.err:
            out = [_clean_ls_proc(p) for p in res.payload]
            if args.dump_file:
                dump_file = Path(args.dump_file).as_posix()
                if not dump_file.endswith('.json'):
                    print('Dump file must be a .json file')
                    sys.exit(1)
                with open(dump_file, 'w') as f:
                    json.dump(out, fp=f, indent=4)
            else:
                print(json.dumps(out, indent=4))

    elif args.subparser == 'load':
        load_file = Path(args.load_file).as_posix()
        if not load_file.endswith('.json'):
            print('[red]File to load must be a json file[/red]')
            sys.exit(1)

        with open(load_file, 'r') as f:
            try:
                prl = json.load(f)
            except json.decoder.JSONDecodeError as e:
                print(f'[red]ERROR:[/red] {load_file} is not a valid json file')
                print(f' -> [red]{e}[/red]')
                sys.exit(1)
        for pr in prl:
            p = Process(**pr)
            if args.load_yes:
                r = 'y'
            else:
                r = input(f'do you want load {p.pm3_name} ({p.pm3_id}) ?')

            if r == 'y':
                post_dest = 'new' if args.load_rewrite is False else 'new/rewrite'
                res = _post(post_dest, p.dict())
                _parse_retmsg(res)
            elif r == 'n':
                print(f'[yellow]skip import {p.pm3_name} ({p.pm3_id})[/yellow]')
            else:
                print(f'[red]only y or n are accepted... skip[/red]')

    else:
        print(parser.format_help())

if __name__ == '__main__':
    main()