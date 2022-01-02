from pydantic import BaseModel, validator
import subprocess as sp
import psutil
import time
import os
from pathlib import Path

class ProcessStatus(BaseModel):
    cmdline: list
    connections: list = None
    cpu_percent: float
    cpu_times: list
    create_time: float
    cwd: str
    exe: str
    gids: list
    io_counters: list
    ionice: list
    memory_info: list
    memory_percent: float
    name: str
    open_files: list
    pid: int
    ppid: int
    status: str
    uids: list
    username: str


class Process(BaseModel):
    cmd: str
    cwd: str = Path.home().as_posix()
    pm3_home: str = Path('~/.pm3/').expanduser().as_posix()
    pm3_name: str
    pm3_id: int
    shell: bool = False
    stdout: str = ''
    stderr: str = ''
    pid: int = None
    autorun: bool = False

    @validator('pm3_name')
    def pm3_name_formatter(cls, v, values, **kwargs):
        v = v or values['cmd'].split(" ")[0]
        v = v.replace(' ', '_').replace('./', '').replace('/', '')
        return v

    @validator('stdout')
    def stdout_formatter(cls, v, values, **kwargs):
        logfile = f"{values['pm3_name']}_{values['pm3_id']}.log"
        v = v or Path(values['pm3_home'], logfile).as_posix()
        return v

    @validator('stderr')
    def stderr_formatter(cls, v, values, **kwargs):
        errfile = f"{values['pm3_name']}_{values['pm3_id']}.err"
        v = v or Path(values['pm3_home'], errfile).as_posix()
        return v

    @property
    def is_running(self):
        if self.pid:
            ps = psutil.Process(self.pid)
            return ps.is_running()
        else:
            return False

    @property
    def ps(self, full=False):
        if full:
            return psutil.Process(self.pid)
        else:
            return ProcessStatus(**psutil.Process(self.pid).as_dict())

    def kill(self):
        if self.pid is None:
            return None

        try:
            ps = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            # Process already killed
            return None

        if ps.is_running():
            for proc in ps.children(recursive=True):
                print(proc.pid)
                proc.kill()
            ps.kill()

        if ps.is_running():
            time.sleep(3)

        if ps.is_running():
            for proc in ps.children(recursive=True):
                print(proc.pid)
                ps.terminate()
            ps.terminate()
        self.pid = None

    def run(self, detach=False):
        fout = open(self.stdout, 'a')
        ferr = open(self.stderr, 'a')
        if isinstance(self.cmd, list):
            cmd = self.cmd
        elif isinstance(self.cmd, str):
            cmd = self.cmd.split(' ')

        if detach:
            if 'nohup' not in cmd[0]:
                cmd.insert(0, '/usr/bin/nohup')
            #print('detach', cmd)
            p = sp.Popen(cmd,
                         cwd=self.cwd,
                         shell=self.shell,
                         stdout=fout,
                         stderr=ferr,
                         preexec_fn=os.setpgrp)
        else:
            p = sp.Popen(cmd,
                         cwd=self.cwd,
                         shell=self.shell,
                         stdout=fout,
                         stderr=ferr)
        self.pid = p.pid
        return p

