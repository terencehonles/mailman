#! /usr/bin/env python3

import os
import re
import stat
import datetime


FSF = 'by the Free Software Foundation, Inc.'
this_year = datetime.date.today().year
pyre = re.compile(r'# Copyright \(C\) ((?P<start>\d{4})-)?(?P<end>\d{4})')

MODE = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)


def do_file(path):
    print('=>', path)
    permissions = os.stat(path).st_mode & MODE
    with open(path) as in_file, open(path + '.out', 'w') as out_file:
        try:
            for line in in_file:
                mo = pyre.match(line)
                if mo is None:
                    out_file.write(line)
                    continue
                start = (mo.group('end')
                         if mo.group('start') is None
                         else mo.group('start'))
                print('# Copyright (C) {}-{} {}'.format(
                      start, this_year, FSF), file=out_file)
                for line in in_file:
                    out_file.write(line)
        except UnicodeDecodeError:
            print('Cannot convert path:', path)
            os.remove(path + '.out')
            return
    os.rename(path + '.out', path)
    os.chmod(path, permissions)


def do_walk():
    for root, dirs, files in os.walk('.'):
        if root == '.':
            dirs.remove('.bzr')
            dirs.remove('bin')
            dirs.remove('contrib')
            dirs.remove('develop-eggs')
            dirs.remove('eggs')
            dirs.remove('parts')
            files.remove('gnu-COPYING-GPL')
            files.remove('.installed.cfg')
            files.remove('.bzrignore')
            files.remove('distribute_setup.py')
        if root == './src':
            dirs.remove('mailman.egg-info')
        if root == './src/mailman':
            dirs.remove('messages')
        for file_name in files:
            if os.path.splitext(file_name)[1] in ('.pyc', '.gz', '.egg'):
                continue
            path = os.path.join(root, file_name)
            if os.path.isfile(path):
                do_file(path)


if __name__ == '__main__':
    do_walk()
