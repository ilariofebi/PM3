from importlib import import_module
import json
import math, random
from subprocess import run
from time import sleep
from types import SimpleNamespace as Namespace
import unittest
unittest.TestLoader.sortTestMethodsUsing = None
from datetime import datetime

module = 'PM3'
test_process_name = 'test_process_name'

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
    with open(file_name) as f:
        return json.loads( f.read())

def my_function(arg):
    rand = random.randint(1,10000)
    sleep(random.randint(1,2))
    print(f"adding process_{rand}", flush=True)
    result = shell(f"python -m {module}.cli new process_{rand}")
    print(f"added process_{rand} exit code {result.exit_code}", flush=True)
    assert result.exit_code == 0
    sleep(random.randint(1,2))
    print(f"removing process_{rand}", flush=True)
    result = shell(f"python -m {module}.cli rm process_{rand}")
    print(f"removed process_{rand} exit code {result.exit_code}", flush=True)
    assert result.exit_code == 0


class TestMultithreading(unittest.TestCase):
    def test_01_multithreading(self):
        """
        Importa modulo per verificare che sia installato correttamente.
        """
        from multiprocessing.dummy import Pool as ThreadPool
        pool = ThreadPool(10)
        results = pool.map(my_function, range(30))

    
if __name__ == "__main__":
    test = TestMultithreading()
    test.test_01_multithreading()