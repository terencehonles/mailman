# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from cPickle import load

from mailman.config import config
from mailman.core.i18n import _
from mailman.options import Options



class ScriptOptions(Options):
    usage = _("""
%%prog [options] qfiles ...

Show the contents of one or more Mailman queue files.""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-q', '--quiet',
            default=False, action='store_true',
            help=_("Don't print 'helpful' message delimiters."))
        self.parser.add_option(
            '-s', '--summary',
            default=False, action='store_true',
            help=_('Show a summary of queue files.'))



def main():
    options = ScriptOptions()
    options.initialize()

    if options.options.summary:
        queue_totals = {}
        files_by_queue = {}
        for switchboard in config.switchboards.values():
            total = 0
            file_mappings = {}
            for filename in os.listdir(switchboard.queue_directory):
                base, ext = os.path.splitext(filename)
                file_mappings[ext] = file_mappings.get(ext, 0) + 1
                total += 1
            files_by_queue[switchboard.queue_directory] = file_mappings
            queue_totals[switchboard.queue_directory] = total
        # Sort by queue name.
        for queue_directory in sorted(files_by_queue):
            total = queue_totals[queue_directory]
            print queue_directory
            print _('\tfile count: $total')
            file_mappings = files_by_queue[queue_directory]
            for ext in sorted(file_mappings):
                print '\t{0}: {1}'.format(ext, file_mappings[ext])
        return
    # No summary.
    for filename in options.arguments:
        if not options.options.quiet:
            print '====================>', filename
        with open(filename) as fp:
            if filename.endswith('.pck'):
                msg = load(fp)
                data = load(fp)
                if data.get('_parsemsg'):
                    sys.stdout.write(msg)
                else:
                    sys.stdout.write(msg.as_string())
            else:
                sys.stdout.write(fp.read())



if __name__ == '__main__':
    main()
