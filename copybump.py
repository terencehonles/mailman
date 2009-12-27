#! /usr/bin/env python3

import os
import re
import datetime


FSF = 'by the Free Software Foundation, Inc.'
this_year = datetime.date.today().year
pyre = re.compile(r'^# Copyright (C) (?P<start>\d{4}-)?(?P<end>\d{4})')


def do_file(path):
    with open(path) as in_file, open(path + '.out', 'w') as out_file:
        for line in in_file:
            mo = pyre.match(line)
            if mo is None:
                out_file.write(line)
                continue
            start = (mo.group('end')
                     if mo.group('start') is None
                     else mo.group('start'))
            print('# Copyright (C) {}-{} {}'.format(
                  mo.group('end'), this_year, FSF), file=out_file)
            for line in in_file:
                out_file.write(line)
    os.rename(path + '.out', path)
