# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
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

import sys
import optparse

from mailman.configuration import config
from mailman.i18n import _
from mailman.queue import Switchboard
from mailman.version import MAILMAN_VERSION



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] [directory]

Move a message from the shunt queue to the original queue.  Optional
`directory' specifies a directory to dequeue from other than qfiles/shunt.
"""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)
    if args:
        qdir = args[0]
    else:
        qdir = config.SHUNTQUEUE_DIR

    sb = Switchboard(qdir)
    sb.recover_backup_files()
    for filebase in sb.files():
        try:
            msg, msgdata = sb.dequeue(filebase)
            whichq = msgdata.get('whichq', config.INQUEUE_DIR)
            tosb = Switchboard(whichq)
            tosb.enqueue(msg, msgdata)
        except Exception, e:
            # If there are any unshunting errors, log them and continue trying
            # other shunted messages.
            print >> sys.stderr, _(
                'Cannot unshunt message $filebase, skipping:\n$e')
        else:
            # Unlink the .bak file left by dequeue()
            sb.finish(filebase)



if __name__ == '__main__':
    main()
