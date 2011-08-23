#! /usr/bin/env python3

import os
import re
import sys
import stat
import datetime


FSF = 'by the Free Software Foundation, Inc.'
this_year = datetime.date.today().year
pyre = re.compile(r'# Copyright \(C\) ((?P<start>\d{4})-)?(?P<end>\d{4})')

MODE = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)


def do_file(path, owner):
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
                if int(start) == this_year:
                    out_file.write(line)
                    continue
                print('# Copyright (C) {}-{} {}'.format(
                      start, this_year, owner), file=out_file)
                for line in in_file:
                    out_file.write(line)
        except UnicodeDecodeError:
            print('Cannot convert path:', path)
            os.remove(path + '.out')
            return
    os.rename(path + '.out', path)
    os.chmod(path, permissions)


def remove(dirs, path):
    try:
        dirs.remove(path)
    except ValueError:
        pass


def do_walk():
    try:
        owner = sys.argv[1]
    except IndexError:
        owner = FSF
    for root, dirs, files in os.walk('.'):
        if root == '.':
            remove(dirs, '.bzr')
            remove(dirs, 'bin')
            remove(dirs, 'contrib')
            remove(dirs, 'develop-eggs')
            remove(dirs, 'eggs')
            remove(dirs, 'parts')
            remove(dirs, 'gnu-COPYING-GPL')
            remove(dirs, '.installed.cfg')
            remove(dirs, '.bzrignore')
            remove(dirs, 'distribute_setup.py')
        if root == './src':
            remove(dirs, 'mailman.egg-info')
        if root == './src/mailman':
            remove(dirs, 'messages')
        for file_name in files:
            if os.path.splitext(file_name)[1] in ('.pyc', '.gz', '.egg'):
                continue
            path = os.path.join(root, file_name)
            if os.path.isfile(path):
                do_file(path, owner)


if __name__ == '__main__':
    do_walk()
