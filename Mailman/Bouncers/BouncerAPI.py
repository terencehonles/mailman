# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
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

import sys
import traceback
from types import ListType
from cStringIO import StringIO

# testing kludge
if __name__ == '__main__':
    execfile('bin/paths.py')

from Mailman.Logging.Syslog import syslog

# If a bounce detector returns Stop, that means to just discard the message.
# An example is warning messages for temporary delivery problems.  These
# shouldn't trigger a bounce notification, but we also don't want to send them
# on to the list administrator.
class _Stop:
    pass
Stop = _Stop()



# msg must be a mimetools.Message
def ScanMessages(mlist, msg, testing=0):
    pipeline = ['DSN',
                'Qmail',
                'Postfix',
                'Yahoo',
                'Caiwireless',
                'Exim',
                'Netscape',
                'Compuserve',
                'Microsoft',
                'GroupWise',
                'SMTP32',
                'SimpleMatch',
                'SimpleWarning',
                'Yale',
                'LLNL',
                ]
    for module in pipeline:
        modname = 'Mailman.Bouncers.' + module
        __import__(modname)
        addrs = sys.modules[modname].process(msg)
        if addrs is Stop:
            return 1
        if addrs:
            for addr in addrs:
                if not addr:
                    continue
                # we found a bounce or a list of bounce addrs
                if not testing:
                    try:
                        mlist.registerBounce(addr, msg)
                    except Exception, e:
                        syslog(
                            'error',
                            'Bouncer exception while processing module %s: %s',
                            module, e)
                        s = StringIO()
                        traceback.print_exc(file=s)
                        syslog('error', s.getvalue())
                        return 0
                else:
                    print '\t%s: detected address <%s>' % (modname, addr)
            # we saw some bounces
            return 1
##        else:
##            if testing:
##                print '\t%11s: no bounces detected' % modname
    # no bounces detected
    return 0



# for testing
if __name__ == '__main__':
    from Mailman import Message
    from Mailman.i18n import _
    import email

    def usage(code, msg=''):
        print >> sys.stderr, _(__doc__)
        if msg:
            print >> sys.stderr, msg
        sys.exit(code)

    if len(sys.argv) < 2:
        usage(1, 'required arguments: <file> [, <file> ...]')

    for filename in sys.argv[1:]:
        print 'scanning file', filename
        fp = open(filename)
        msg = email.message_from_file(fp, Message.Message)
        fp.close()
        ScanMessages(None, msg, testing=1)
