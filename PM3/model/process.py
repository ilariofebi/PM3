from pydantic import BaseModel, validator, root_validator
from typing import Union
import subprocess as sp
import psutil
import time
import os
from pathlib import Path
import pendulum
import signal

class KillMsg(BaseModel):
    msg: str = ''
    err: bool = False
    warn: bool = False
    gone: list = []
    alive: list = []

class ProcessStatusLight(BaseModel):
    pm3_id: int
    pm3_name: str
    cmdline: Union[list, str]
    cpu_percent: float
    create_time: Union[float, str]
    cwd: Union[str, None]
    exe: str
    memory_percent: float
    name: str
    ppid: int
    pid: int
    status: str
    username: str
    cmd: str
    restart: int
    autorun: bool

    @validator('memory_percent')
    def memory_percent_formatter(cls, v):
        v = round(v, 2)
        return v

    @validator('cmdline')
    def cmdline_formatter(cls, v):
        if isinstance(v, list):
            v = ' '.join(v)
        return v

    @validator('create_time')
    def create_time_formatter(cls, v):
        if isinstance(v, float):
            v = pendulum.from_timestamp(v).astimezone().format('DD/MM/YYYY HH:mm:ss')
        return v

class ProcessStatus(BaseModel):
    cmdline: list
    connections: Union[list, None]
    cpu_percent: float
    cpu_times: list
    create_time: float
    cwd: Union[str, None]
    exe: str
    gids: list
    io_counters: Union[list, None]
    ionice: list
    memory_info: list
    memory_percent: float
    name: str
    open_files: Union[list, None]
    pid: int
    ppid: int
    status: str
    uids: list
    username: str

    cmd: str
    interpreter: str
    pm3_home: str
    pm3_name: str
    pm3_id: int
    shell: bool
    stdout: str
    stderr: str
    restart: int
    autorun: bool
    nohup: bool


class Process(BaseModel):
    pm3_id: int
    pm3_name: str
    cmd: str
    cwd: str = Path.home().as_posix()
    pid: int = -1
    pm3_home: str = Path('~/.pm3/').expanduser().as_posix()
    restart: int = 0
    shell: bool = False
    autorun: bool = False
    interpreter: str = ''
    stdout: str = ''
    stderr: str = ''
    nohup: bool = False

    @root_validator
    def _formatter(cls, values):
        # pm3_name
        values['pm3_name'] = values['pm3_name'] or values['cmd'].split(" ")[0]
        values['pm3_name'] = values['pm3_name'].replace(' ', '_').replace('./', '').replace('/', '')

        # stdout
        logfile = f"{values['pm3_name']}_{values['pm3_id']}.log"
        values['stdout'] = values['stdout'] or Path(values['pm3_home'], logfile).as_posix()

        # stderr
        errfile = f"{values['pm3_name']}_{values['pm3_id']}.err"
        values['stderr'] = values['stderr'] or Path(values['pm3_home'], errfile).as_posix()
        return values

    @property
    def is_running(self):
        if self.pid > 0:
            try:
                ps = self.ps(full=True)
            except psutil.NoSuchProcess:
                self.pid = -1
                return False
            if ps.status() == 'zombie':
                return True
            if Path(self.cwd) == Path(ps.cwd()):
                # Minimal check for error in pid
                return ps.is_running()
            self.pid = -1
            return False
        else:
            self.pid = -1
            return False

    def ps(self, full=False):
        if full:
            return psutil.Process(self.pid)
        else:
            return ProcessStatus(**psutil.Process(self.pid).as_dict())

    @staticmethod
    def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                       timeout=None, on_terminate=None):
        """Kill a process tree (including grandchildren) with signal
        "sig" and return a (gone, still_alive) tuple.
        "on_terminate", if specified, is a callback function which is
        called as soon as a child terminates.
        """
        parent = psutil.Process(pid)
        # Kill Parent and Children
        children = parent.children(recursive=True)
        if include_parent:
            children.append(parent)

        for p in children:
            try:
                p.send_signal(sig)
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(children, timeout=timeout,
                                        callback=on_terminate)
        return (gone, alive)

    def kill(self):
        if self.pid == -1:
            return KillMsg(msg='NOT RUNNING', warn=True)
        try:
            psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            return KillMsg(msg='NO SUCH PROCESS', warn=True)

        gone, alive = self.kill_proc_tree(self.pid)
        if len(alive) > 0:
            return KillMsg(msg='OK', alive=alive, gone=gone, warn=True)
        else:
            self.pid = -1
            return KillMsg(msg='OK', alive=alive, gone=gone)

    def run(self):
        fout = open(self.stdout, 'a')
        ferr = open(self.stderr, 'a')
        if isinstance(self.cmd, list):
            cmd = self.cmd
        elif isinstance(self.cmd, str):
            cmd = self.cmd.split(' ')
        else:
            return False

        if Path(self.interpreter).is_file():
            cmd.insert(0, self.interpreter)

        if self.nohup:
            if 'nohup' not in cmd[0]:
                cmd.insert(0, '/usr/bin/nohup')
            # print('detach', cmd)
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
        self.restart += 1
        return p

    def reset(self):
        self.restart = 0