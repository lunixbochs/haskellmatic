from sublimelint.lint.linter import Linter
import os

from .daemon import get_daemon, find_sentinel

class Haskell(Linter):
    cmd = ('ghc-modi', '-g', 'Wall')
    language = 'haskell'
    regex = r'^.+?:(?P<line>\d+):(?P<col>\d+):\s*(?P<error>.+)'
    sentinel = '*.cabal'

    def run(self, cmd, code):
        if self.filename:
            root = find_sentinel(self.filename, self.sentinel)
            root = root or os.path.dirname(self.filename)
        else:
            root = ''
        daemon = get_daemon(root, cmd)
        if daemon:
            lines = daemon.check(self.filename, code)
            lines = [line.replace('\x00', ' ') for line in lines]
            return '\n'.join(lines) + '\n'
