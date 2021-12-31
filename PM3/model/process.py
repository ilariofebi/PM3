from pydantic import BaseModel
import subprocess as sp
import psutil
import time
import os

class Process(BaseModel):
    cmd: str
    pm3_name: str
    pm3_id: int
    shell: bool = False
    stdout: str = ''
    stderr: str = ''
    pid: int = None
    autorun: bool = False

    @property
    def is_running(self):
        if self.pid:
            ps = psutil.Process(self.pid)
            return ps.is_running()
        else:
            return False

    @property
    def ps(self):
        return psutil.Process(self.pid)

    def kill(self):
        if self.pid is None:
            return None

        ps = psutil.Process(self.pid)
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
                         shell=self.shell,
                         stdout=fout,
                         stderr=ferr,
                         preexec_fn=os.setpgrp)
        else:
            p = sp.Popen(cmd,
                         shell=self.shell,
                         stdout=fout,
                         stderr=ferr)
        self.pid = p.pid
        return p