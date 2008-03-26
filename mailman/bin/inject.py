# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

from __future__ import with_statement

import os
import sys

from mailman import Utils
from mailman import Version
from mailman.configuration import config
from mailman.i18n import _
from mailman.inject import inject
from mailman.options import SingleMailingListOptions



class ScriptOptions(SingleMailingListOptions):
    usage=_("""\
%prog [options] [filename]

Inject a message from a file into Mailman's incoming queue.  'filename' is the
name of the plaintext message file to inject.  If omitted, or the string '-',
standard input is used.
""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-q', '--queue',
            type='string', help=_("""\
The name of the queue to inject the message to.  The queuename must be one of
the directories inside the qfiles directory.  If omitted, the incoming queue
is used."""))

    def sanity_check(self):
        if not self.options.listname:
            self.parser.error(_('Missing listname'))
        if len(self.arguments) == 0:
            self.filename = '-'
        elif len(self.arguments) > 1:
            self.parser.print_error(_('Unexpected arguments'))
        else:
            self.filename = self.arguments[0]



def main():
    options = ScriptOptions()
    options.initialize()

    if options.options.queue is None:
        qdir = config.INQUEUE_DIR
    else:
        qdir = os.path.join(config.QUEUE_DIR, options.options.queue)
        if not os.path.isdir(qdir):
            options.parser.error(_('Bad queue directory: $qdir'))

    fqdn_listname = options.options.listname
    mlist = config.db.list_manager.get(fqdn_listname)
    if mlist is None:
        options.parser.error(_('No such list: $fqdn_listname'))

    if options.filename == '-':
        message_text = sys.stdin.read()
    else:
        with open(options.filename) as fp:
            message_text = fp.read()

    inject(fqdn_listname, message_text, qdir=qdir)



if __name__ == '__main__':
    main()
