import subprocess
import time
import unittest

import psutil

from PM3.model.process import Process


class TestProcessKillTree(unittest.TestCase):
    def test_kill_proc_tree_stops_parent_and_child(self):
        parent = subprocess.Popen(
            [
                "python",
                "-c",
                "import subprocess,time; subprocess.Popen(['sleep','60']); time.sleep(60)",
            ]
        )
        time.sleep(1)
        proc = psutil.Process(parent.pid)
        children = proc.children(recursive=True)
        self.assertTrue(children)

        gone, alive = Process.kill_proc_tree(parent.pid)
        self.assertFalse(alive)
        self.assertTrue(any(getattr(p, "pid", None) == parent.pid for p in gone))
        self.assertFalse(psutil.pid_exists(parent.pid))
        for child in children:
            self.assertFalse(psutil.pid_exists(child.pid))
        parent.wait(timeout=1)


if __name__ == "__main__":
    unittest.main()
