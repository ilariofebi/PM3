import time

import requests
from PM3.model.pm3_protocol import RetMsg
from PM3.model.process import Process
from rich import print
from pathlib import Path
from configparser import ConfigParser

#Read Config:
pm3_home_dir = Path('~/.pm3').expanduser()
config_file = f'{pm3_home_dir}/config.ini'
if not Path(config_file).is_file():
    raise Exception('Run pm3 first')

config = ConfigParser()
config.read(config_file)
base_url = config['backend'].get('url')
sleep_time = int(config['cron_checker'].get('sleep_time'))

def _get(path) -> RetMsg:
    #TODO: duplicato presente in cli.py
    try:
        r = requests.get(f'{base_url}/{path}')
    except requests.exceptions.ConnectionError as e:
        return RetMsg(err=True, msg=str(e))

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
                    # Restart OK
                    print(res_start.payload[0]['msg'])
                else:
                    # Restart ERROR
                    print(res_start)
            elif config['cron_checker'].get('debug'):
                print('process running:')
                print(p)
    else:
        print(res)

def main():
    while True:
        check_autostart()
        time.sleep(sleep_time)

if __name__ == '__main__':
    main()
