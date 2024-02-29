from logging.handlers import RotatingFileHandler
import threading, logging
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Union
import subprocess as sp
import psutil
import os
from pathlib import Path
import pendulum
import signal
from PM3.model.pm3_protocol import KillMsg, alive_gone

# TODO: Trovare nomi milgiori

def on_terminate(proc):
    pass
    #print(proc.status())
    #print("process {} terminated with exit code {}".format(proc.pid, proc.returncode))


class ProcessStatusLight(BaseModel):
    pm3_id: int
    pm3_name: str
    cmdline: Union[list, str]
    cpu_percent: float
    create_time: Union[float, str]
    time_ago: str = ''
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

    @field_validator('memory_percent')
    def memory_percent_formatter(cls, v):
        v = round(v, 2)
        return v

    @field_validator('cmdline')
    def cmdline_formatter(cls, v):
        if isinstance(v, list):
            v = ' '.join(v)
        return v

    @model_validator(mode='after')
    def time_ago_generator(self):
        create_time = pendulum.from_timestamp(self.create_time)
        time_ago = pendulum.now() - create_time
        self.time_ago = time_ago.in_words()

    @field_validator('create_time')
    def create_time_formatter(cls, v, values, **kwargs):
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

class LogPipe(threading.Thread):

    def __init__(self, filename, level = logging.DEBUG):
        """Setup the object with a logger and a loglevel
        and start the thread
        """
        # nuovo logger
        from uuid import uuid4
        logger = logging.getLogger( str(uuid4()))
        handler = RotatingFileHandler(filename, maxBytes=1000*1000*30, backupCount=20)
        logger.level = level
        handler.level = level
        logger.addHandler( handler )

        threading.Thread.__init__(self)
        self.daemon = False
        self.level = level
        self.logger = logger
        self.fdRead, self.fdWrite = os.pipe()
        self.pipeReader = os.fdopen(self.fdRead)

        self.start()

    def fileno(self):
        """Return the write file descriptor of the pipe
        """
        return self.fdWrite

    def run(self):
        """Run the thread, logging everything.
        """
        for line in iter(self.pipeReader.readline, ''):
            self.logger.log(self.level, line.strip('\n'))

        self.pipeReader.close()

    def close(self):
        """Close the write end of the pipe.
        """
        os.close(self.fdWrite)


    # Utilizzata per mostrare i dati in formato tabellare

    pm3_name: str
    cmd: str
    cwd: str = Path.home().as_posix()
    pid: Union[int, None] = -1
    restart: Union[int, str] = ''
    running: bool = False
    autorun: Union[bool, str] = False





class Process(BaseModel):
    # Struttura vera del processo
    pm3_id: Optional[int] = Field(default=None, json_schema_extra={'list': True})  # None significa che deve essere assegnato da next_id()
    pm3_name: str = Field(json_schema_extra={'list': True})
    cmd: str = Field(json_schema_extra={'list': True})
    cwd: Optional[str] = Field(default= Path.home().as_posix() , json_schema_extra={'list': True})
    pid: int = Field(default=-1 , json_schema_extra={'list': True})
    pm3_home: Optional[str] = Path('~/.pm3/').expanduser().as_posix()
    restart: int = Field(default=-1)
    shell: bool = False
    autorun: bool = Field(default=False, json_schema_extra={'list': False})
    interpreter: str = ''
    stdout: str = ''
    stderr: str = ''
    nohup: bool = False
    max_restart: Optional[int] = 1000
    autorun_exclude : bool = False
    running: bool = Field(default=False, json_schema_extra={'list': True})
    autorun_status: Optional[str] = Field(default=None, json_schema_extra={'list': True} )
    restart_status: Optional[str] = Field(default=None, json_schema_extra={'list': True} )

    @model_validator(mode='after')
    def _formatter(self):
        # pm3_name

        self.pm3_name = self.pm3_name or self.cmd.split(" ")[0]
        self.pm3_name = self.pm3_name.replace(' ', '_').replace('./', '').replace('/', '')

        # stdout
        logfile = f"{self.pm3_name}_{self.pm3_id}.log"
        self.stdout = self.stdout or Path(self.pm3_home, 'log', logfile).as_posix()

        # stderr
        errfile = f"{self.pm3_name}_{self.pm3_id}.err"
        self.stderr = self.stdout or Path(self.pm3_home, 'log', errfile).as_posix()

        # Fromatting running
        self.running = True if self.pid > 0 else False

        # Formatting pid
        self.pid = self.pid if self.pid > 0 else None

        if self.autorun is False:
            self.autorun_status = '[red]disabled[/red]'
        elif self.autorun and self.autorun_exclude:
            self.autorun_status = '[yellow]suspended[/yellow]'
        elif self.autorun and not self.autorun_exclude:
            self.autorun_status = '[green]enabled[/green]'

        # Formatting restart
        n_restart = self.restart if self.restart > 0 else 0
        self.restart_status = f"{n_restart}/{self.max_restart}"

    @property
    def is_running(self):
        if self.pid > 0:

            try:
                # Verifico che il pid esita ancora
                ps = self.ps(full=True)
                # Verifico che il pid appartenga all'UID corrente
                ps_cwd = ps.cwd()
            except psutil.NoSuchProcess:
                self.pid = -1
                return False
            except psutil.AccessDenied:
                self.pid = -1
                return False

            if ps.status() == 'zombie':
                return True

            if Path(self.cwd) == Path(ps_cwd):
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
                       timeout=5, on_terminate=on_terminate):
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
        try:
            gone, alive = psutil.wait_procs(children, timeout=timeout,
                                            callback=on_terminate)
        except psutil.NoSuchProcess:
            gone = [alive_gone(pid=pid),]
            alive = []

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
        #fErrHandler = RotatingFileHandler(self.stderr, maxBytes=1000*1000*10, backupCount=5)
        #fout = LogPipe(self.stderr)
        #ferr = LogPipe(self.stdout)
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
            # print("starting with nohup")
            if 'nohup' not in cmd[0]:
                cmd.insert(0, '/usr/bin/nohup')
            # print('detach', cmd)
            p = sp.Popen(cmd,
                         cwd=self.cwd,
                         shell=self.shell,
                         stdout=fout,
                         stderr=ferr,
                         bufsize=0,
                         preexec_fn=os.setpgrp)
        else:
            print("starting w/o nohup")
            p = sp.Popen(cmd,
                         cwd=self.cwd,
                         shell=self.shell,
                         stdout=fout,
                         stderr=ferr,
                         bufsize=0)
        self.pid = p.pid
        self.restart += 1
        self.autorun_exclude = False
        return p

    def reset(self):
        self.restart = 0