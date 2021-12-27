from flask import Flask, request
from tinydb import TinyDB, where
from model.process import Process
import logging
import json

db = TinyDB('/tmp/pm3_db.json')
tbl = db.table('pm3_procs')

#from flask_crontab import Crontab

app = Flask(__name__)
#crontab = Crontab(app)


@app.post("/new")
def new_process():
    logging.debug(request.json)
    P = Process(**request.json)
    if tbl.contains(where('pm3_name') == P.pm3_name):
        logging.info('Processo esistente')
    else:
        tbl.insert(P.dict())
    return P.json()

@app.get("/ls")
def ls_process():
    return json.dumps(tbl.all())

@app.get("/start")
def start_process():
    # id or name
    args = {k: v for k, v in request.args.items()}
    print(args)
    return args


@app.get("/stop")
def stop_process():
    # id or name
    args = {k: v for k, v in request.args.items()}
    print(args)
    return args


@app.get("/restart")
def restart_process():
    # id or name
    pass


#@crontab.job(minute="*")
#def watchdog():
#    print('cron')


if __name__ == '__main__':
    app.run(debug=True)
