# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

"""Decorate a message by sticking the header and footer around it.
"""

import mimelib.Text

from Mailman import mm_cfg
from Mailman.SafeDict import SafeDict
from Mailman.Logging.Syslog import syslog



def process(mlist, msg, msgdata):
    if msgdata.get('isdigest'):
        # Digests already have their own header and footer
        return
    header = decorate(mlist, mlist.msg_header, 'non-digest header')
    footer = decorate(mlist, mlist.msg_footer, 'non-digest footer')
    # Be MIME smart here.  If the message is non-multipart, then we can just
    # tack the header and footers onto the message body.  But if the message
    # is multipart, we want to add them as MIME subobjects.
    if msg.ismultipart():
        mimehdr = mimelib.Text(header)
        mimeftr = mimelib.Text(footer)
        payload = msg.get_payload()
        payload.insert(0, mimehdr)
        payload.append(mimeftr)
    else:
        payload = header + msg.get_payload() + footer
        msg.set_payload(payload)



def decorate(mlist, template, what):
    # `what' is just a descriptive phrase
    d = SafeDict(mlist.__dict__)
    # Certain attributes are sensitive
    del d['password']
    del d['passwords']
    d['cgiext'] = mm_cfg.CGIEXT
    # Interpolate into the template
    try:
        text = (template % d).replace('\r\n', '\n')
    except ValueError, e:
        syslog('error', 'Exception while calculating %s:\n%s' %
               (what, e))
        text = '[INVALID %s]' % what.upper()
    return text
