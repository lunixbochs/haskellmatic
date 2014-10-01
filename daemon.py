from sublimelint.lint.util import climb, memoize, popen

from contextlib import contextmanager
from queue import Queue, Empty
import glob
import os
import tempfile
import threading
import time

try:
    daemons
except NameError:
    daemons = {}

@memoize
def find_sentinel(filename, sentinel):
    top = os.path.dirname(filename)
    if glob.glob(os.path.join(top, sentinel)):
        return top

    for d in climb(top):
        target = os.path.join(d, sentinel)
        if glob.glob(target):
            return d

@contextmanager
def chdir(path):
    old = os.getcwd()
    if path:
        os.chdir(path)
    yield
    chdir(old)

class Daemon:
    def __init__(self, root, cmd):
        self.tmpfiles = {}
        self.queue = Queue()

        with chdir(root):
            proc = popen(cmd)
        self.proc = proc
        thread = threading.Thread(target=self.read_thread)
        thread.daemon = True
        thread.start()

    def read_thread(self):
        while self.running:
            line = self.proc.stdout.readline().decode('utf8').strip()
            self.queue.put(line)

    @property
    def running(self):
        return self.proc.poll() is None

    def send(self, msg):
        if self.running:
            self.proc.stdin.write((msg + '\n').encode('utf8'))
            return self.read()

    def read(self, timeout=5):
        lines = []
        start = time.time()
        line = ''
        if self.queue.empty():
            time.sleep(0.1)
        while self.running and time.time() - start < timeout:
            try:
                line = self.queue.get(False)
                lines.append(line)
            except Empty:
                if line == 'OK':
                    break
        return lines

    def ok(self):
        if self.running:
            response = self.send('.')
            if response and response[-1] == 'OK':
                return True
        return False

    def check(self, filename, code):
        if not filename in self.tmpfiles:
            self.tmpfiles[filename] = tempfile.NamedTemporaryFile(suffix='.hs')
        f = self.tmpfiles[filename]
        f.seek(0)
        f.truncate()
        f.write(code.encode('utf8'))
        f.flush()

        if self.running:
            response = self.send('check {}'.format(f.name))
            return response
        return []

def get_daemon(filename, cmd, sentinel='*.cabal'):
    root = find_sentinel(filename, sentinel)
    root = root or os.path.dirname(filename)
    daemon = daemons.get(root)
    if daemon and daemon.ok():
        return daemon
    else:
        daemons[root] = Daemon(root, cmd)
