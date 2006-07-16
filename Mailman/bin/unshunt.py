# Copyright (C) 2002-2006 by the Free Software Foundation, Inc.
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

import sys
import optparse

from Mailman import mm_cfg
from Mailman.Queue.sbcache import get_switchboard
from Mailman.i18n import _

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=mm_cfg.MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] [directory]

Move a message from the shunt queue to the original queue.  Optional
`directory' specifies a directory to dequeue from other than qfiles/shunt.
"""))
    opts, args = parser.parse_args()
    if len(args) > 1:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    if args:
        qdir = args[0]
    else:
        qdir = mm_cfg.SHUNTQUEUE_DIR

    sb = get_switchboard(qdir)
    sb.recover_backup_files()
    for filebase in sb.files():
        try:
            msg, msgdata = sb.dequeue(filebase)
            whichq = msgdata.get('whichq', mm_cfg.INQUEUE_DIR)
            tosb = get_switchboard(whichq)
            tosb.enqueue(msg, msgdata)
        except Exception, e:
            # If there are any unshunting errors, log them and continue trying
            # other shunted messages.
            print >> sys.stderr, _(
                'Cannot unshunt message $filebase, skipping:\n$e')
        else:
            # Unlink the .bak file left by enqueue()
            tosb.finish(filebase)



if __name__ == '__main__':
    main()
