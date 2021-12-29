#!/usr/bin/env python3

import requests
from tabulate import tabulate
import argparse
import logging
from model.process import Process
from rich import print

logging.basicConfig(level=logging.DEBUG)
base_url = 'http://127.0.0.1:5000/'

def _get(path):
    r = requests.get(f'{base_url}/{path}')
    if r.status_code == 200:
        return r.json()
    else:
        return {}

def _post(path, jdata):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='pm3', description='Like pm2 without node.js')
    subparsers = parser.add_subparsers(dest='subparser')

    parser_ls = subparsers.add_parser('ls', help='show process')

    parser_save = subparsers.add_parser('save', help='save process config into db')

    parser_new = subparsers.add_parser('new', help='create a new process')
    parser_new.add_argument('cmd', help='linux command')
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

    if args.subparser == 'ls':
        if ls := _ls():
            print(ls)
        else:
            print('---')

    elif args.subparser == 'new':
        pm3_name = args.pm3_name or ''
        pm3_id = args.pm3_id or 0
        pm3_shell = args.pm3_shell or False
        pm3_autorun = args.pm3_autorun or False
        pm3_stdout = args.pm3_stdout or ''
        pm3_stderr = args.pm3_stderr or ''

        p = Process(cmd=args.cmd,
                    pm3_name=pm3_name,
                    pm3_id=pm3_id,
                    shell=pm3_shell,
                    autorun=pm3_autorun,
                    stdout=pm3_stdout,
                    stderr=pm3_stderr)
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

    else:
        print(parser.format_help())
