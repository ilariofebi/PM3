from importlib import import_module
import json, os
from subprocess import run
from types import SimpleNamespace as Namespace
import unittest
unittest.TestLoader.sortTestMethodsUsing = None
from datetime import datetime

module = 'PM3'
test_process_name = 'test_process_name'
run_anyway_dangerous_if_true = True


def shell(command, **kwargs):
    """
    Execute a shell command capturing output and exit code.

    This is a better version of ``os.system()`` that captures output and
    returns a convenient namespace object.
    """
    completed = run(command, shell=True, capture_output=True, check=False, **kwargs)

    return Namespace(
        exit_code=completed.returncode,
        stdout=completed.stdout.decode(),
        stderr=completed.stderr.decode(),
    )

def dump_and_read_json():
    file_name = "test0dump_" + datetime.now().strftime("%d%m%Y-%H%M%S.%f") + ".json"
    result = shell(f"python -m {module}.cli dump --file " + file_name)

    assert result.exit_code == 0

    # deve esserci il nome del file
    assert os.path.exists(file_name)

    with open(file_name) as f:
        return json.loads( f.read())



class TestShell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Another daemon already running?"""
        if run_anyway_dangerous_if_true:
            return # bypass daemon check (for debugging)
        
        result = shell(f"python -m {module}.cli ping")
        if (result.exit_code == 0):
            print("""Another daemon already running! Another active instance!
                  ps: take care! With test all tasks will be purged.""")
            exit(-1)

    def test_01_main_module(self):
        """
        Importa modulo per verificare che sia installato correttamente.
        """
        import_module(f"{module}")

    def test_02_async_daemon_start(self):
        if run_anyway_dangerous_if_true:
            return # do not start the daemon
        
        result = shell(f"python -m {module}.cli daemon start")
        assert result.exit_code == 0

    def test_03_dump(self):
        # facciamo un dump per backup
        result = shell(f"python -m {module}.cli dump --file test_dump_" + datetime.now().strftime("%d%m%Y-%H%M%S.%f") + ".json")
        assert result.exit_code == 0

    def test_04_pre_test_add_process(self):
        result = shell(f"python -m {module}.cli new {test_process_name}") # ora di sicuro l'aggiunta deve andare e buon fine
        assert result.exit_code == 0

    def test_04_purge_process(self):
        result = shell(f"python -m {module}.cli rm all") # rimuovi ma non ti interessare del risultato
        assert result.exit_code == 0

    def test_05_dump_test_purged(self):
        # facciamo un dump per backup
        # contolliamo poi che il file esista!
        if len(dump_and_read_json()) != 0:
            assert False

    def test_05_test_add_process(self):
        result = shell(f"python -m {module}.cli new {test_process_name}") # ora di sicuro l'aggiunta deve andare e buon fine
        assert result.exit_code == 0

    def test_06_remove_process_success(self):
        result = shell(f"python -m {module}.cli rm {test_process_name}") # e di nuovo rimuovi e accertati che l'exit code sia 0
        assert result.exit_code == 0
        result = shell(f"python -m {module}.cli rm {test_process_name}") # e di nuovo rimuovi e accertati che l'exit code sia 0
        assert result.exit_code != 0

    def test_07_test_add_again_process(self):
        result = shell(f'python -m {module}.cli new "sleep 100" --name {test_process_name}') # ora di sicuro l'aggiunta deve andare e buon fine
        assert result.exit_code == 0

    def test_08_test_start(self):
        result = shell(f"python -m {module}.cli start {test_process_name}")
        assert result.exit_code == 0

    def test_09_test_stop(self):
        result = shell(f"python -m {module}.cli start {test_process_name}")
        assert result.exit_code == 0

    def test_10a_test_ls(self):
        result = shell(f"python -m {module}.cli ls")
        assert result.exit_code == 0

    def test_10b_test_ls(self):
        result = shell(f"python -m {module}.cli ls -j")
        assert result.exit_code == 0

    def test_10c_test_ls(self):
        result = shell(f"python -m {module}.cli ls -l")
        assert result.exit_code == 0

    def test_11_dump(self):
        # facciamo un dump per backup
        if len(dump_and_read_json()) != 1:
            assert False

    def test_12_test_restart(self):
        result = shell(f"python -m {module}.cli restart {test_process_name}")
        assert result.exit_code == 0

    def test_13_async_daemon_stop(self):
        result = shell(f"python -m {module}.cli daemon stop")
        assert result.exit_code == 0
