# Copyright (C) 1998 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Contains all the common functionality for msg bounce scanning API.

This module can also be used as the basis for a bounce detection testing
framework.  When run as a script, it expects two arguments, the listname and
the filename containing the bounce message.

"""

# testing kludge
if __name__ == '__main__':
    execfile('bin/paths.py')

from types import ListType
from Mailman import mm_cfg
from Mailman import Errors



# msg must be a mimetools.Message
def ScanMessages(mlist, msg, testing=0):
    pipeline = ['DSN',
                'Qmail',
                'Postfix',
                'Yahoo',
                'Caiwireless',
                'Catchall',
                ]
    for modname in pipeline:
        mod = __import__('Mailman.Bouncers.'+modname)
        func = getattr(getattr(getattr(mod, 'Bouncers'), modname), 'process')
        addrs = func(mlist, msg)
        if addrs:
            for addr in addrs:
                # we found a bounce or a list of bounce addrs
                if not testing:
                    mlist.RegisterBounce(addr, msg)
                else:
                    print 'Bounce of %s detected by module %s' % (
                        addr, modname)
            # we saw some bounces
            return 1
    # no bounces detected
    return 0



# for testing
if __name__ == '__main__':
    import mimetools
    from Mailman import MailList

    def usage(code, msg=''):
        print __doc__
        if msg:
            print msg
        sys.exit(code)

    if len(sys.argv) <> 3:
        usage(1, 'required arguments: <listname> <filename>')

    listname = sys.argv[1]
    filename = sys.argv[2]

    mlist = MailList.MailList(listname, lock=0)
    fp = open(filename)
    msg = mimetools.Message(fp)
    ScanMessages(mlist, msg, testing=1)
