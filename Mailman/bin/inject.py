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

import os
import sys
import optparse

from Mailman import Utils
from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.inject import inject



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [filename]

Inject a message from a file into Mailman's incoming queue.  'filename' is the
name of the plaintext message file to inject.  If omitted, standard input is
used.
"""))
    parser.add_option('-l', '--listname',
                      type='string', help=_("""\
The name of the list to inject this message to.  Required."""))
    parser.add_option('-q', '--queue',
                      type='string', help=_("""\
The name of the queue to inject the message to.  The queuename must be one of
the directories inside the qfiles directory.  If omitted, the incoming queue
is used."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    if opts.listname is None:
        parser.print_help()
        print >> sys.stderr, _('-l is required')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    if opts.queue:
        qdir = os.path.join(config.QUEUE_DIR, opts.queue)
        if not os.path.isdir(qdir):
            parser.print_help()
            print >> sys.stderr, _('Bad queue directory: $qdir')
            sys.exit(1)
    else:
        qdir = config.INQUEUE_DIR

    if not Utils.list_exists(opts.listname):
        parser.print_help()
        print >> sys.stderr, _('No such list: $opts.listname')
        sys.exit(1)

    if args:
        fp = open(args[0])
        try:
            msgtext = fp.read()
        finally:
            fp.close()
    else:
        msgtext = sys.stdin.read()

    inject(opts.listname, msgtext, qdir=qdir)



if __name__ == '__main__':
    main()
