from pydantic import BaseModel
import subprocess as sp
import psutil
import time

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

    def run(self):
        fn = self.cmd.split('/')[-1]
        if not self.stdout:
            self.stdout = f'/tmp/{fn}.out'
        fout = open(self.stdout, 'a')

        if not self.stderr:
            self.stdout = f'/tmp/{fn}.err'
        ferr = open(self.stderr, 'a')

        p = sp.Popen(self.cmd,
                     shell=self.shell,
                     stdout=fout,
                     stderr=ferr)
        self.pid = p.pid
        return p