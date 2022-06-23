import json
import time

import requests
from PM3.model.pm3_protocol import RetMsg
from PM3.model.process import Process
from rich import print
import os, signal
from pathlib import Path
from configparser import ConfigParser
import psutil

DEBUG = True
cron_sleep_time = 5

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

def _get(path) -> RetMsg:
    config = _read_config()
    base_url = config['main_section'].get('backend_url')
    r = requests.get(f'{base_url}/{path}')
    if r.status_code == 200:
        ret = r.json()
        return RetMsg(**ret)
    else:
        return RetMsg(err=True, msg='Connection Error')

def check_autostart():
    res = _get("ls/autorun_enabled")
    if res.err is False:
        payload = res.payload
        # Autorun
        for proc in payload:
            p = Process(**proc)
            if p.pid == -1:
                res_start = _get(f"start/{p.pm3_id}")
                if res_start.err is False:
                    print(res_start.payload[0]['msg'])
                else:
                    print(res_start)
            elif DEBUG:
                print('process running:')
                print(p)

while True:
    check_autostart()
    time.sleep(cron_sleep_time)