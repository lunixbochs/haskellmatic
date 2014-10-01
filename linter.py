from sublimelint.lint.highlight import Highlight
from sublimelint.lint.linter import Linter
from sublimelint.lint import persist
import re

from .daemon import get_daemon

class Haskell(Linter):
    cmd = ('ghc-modi', '-g', 'Wall')
    language = 'haskell'
    regex = r'^.+?:(?P<line>\d+):(?P<col>\d+):\s*(?P<error>.+)'
    sentinel = '*.cabal'

    def reset(self, *args, **kwargs):
        super().reset(*args, **kwargs)
        self.warning_highlight = Highlight(code=self.code, scope='string')
        self.highlights.add(self.warning_highlight)

    def lint(self):
        daemon = get_daemon(self.filename, self.cmd, self.sentinel)
        if daemon:
            lines = daemon.check(self.filename, self.code)
            out = '\n'.join(line.split(':', 1)[1] for line in lines if ':' in line)
            persist.debug('ghc-modi: ' + out)
            errors = []
            warnings = []
            for line in lines:
                line = re.sub(r'\x00|\s{2,}', '', line)
                tup = self.match_error(self.regex, line)
                error = tup[3]
                if error.startswith('Warning:'):
                    warnings.append(tup)
                else:
                    errors.append(tup)
            self.mark_errors(errors)
            self.mark_errors(warnings, highlight=self.warning_highlight)
