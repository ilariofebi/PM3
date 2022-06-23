import time

import requests
from PM3.model.pm3_protocol import RetMsg
from PM3.model.process import Process
from rich import print
from pathlib import Path
from configparser import ConfigParser


def _read_config():
    pm3_home_dir = Path('~/.pm3').expanduser()
    config_file = f'{pm3_home_dir}/config.ini'
    if not Path(config_file).is_file():
        raise Exception('Run pm3 first')
    config = ConfigParser()
    config.read(config_file)
    return config

def _get(path, config) -> RetMsg:
    base_url = config['backend'].get('url')
    r = requests.get(f'{base_url}/{path}')
    if r.status_code == 200:
        ret = r.json()
        return RetMsg(**ret)
    else:
        return RetMsg(err=True, msg='Connection Error')

def check_autostart(config):
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
            elif config['cron_checker'].get('debug'):
                print('process running:')
                print(p)

def main():
    config = _read_config()
    while True:
        check_autostart(config)
        time.sleep(config['cron_checker'].get('sleep_time'))

if __name__ == '__main__':
    main()
