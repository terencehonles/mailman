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

"""Decorate a message by sticking the header and footer around it.
"""

from types import ListType
from email.MIMEText import MIMEText

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.i18n import _
from Mailman.SafeDict import SafeDict
from Mailman.Logging.Syslog import syslog



def process(mlist, msg, msgdata):
    if msgdata.get('isdigest'):
        # Digests already have their own header and footer
        return
    d = {}
    if msgdata.get('personalized'):
        # Calculate the extra personalization dictionary.  Note that the
        # length of the recips list better be exactly 1.
        recips = msgdata.get('recips')
        assert type(recips) == ListType and len(recips) == 1
        member = recips[0].lower()
        d['user_address'] = member
        try:
            d['user_delivered_to'] = mlist.getMemberCPAddress(member)
            # BAW: Hmm, should we allow this?
            d['user_password'] = mlist.getMemberPassword(member)
            d['user_language'] = mlist.getMemberLanguage(member)
            d['user_name'] = mlist.getMemberName(member) or _('not available')
            d['user_optionsurl'] = mlist.GetOptionsURL(member)
        except Errors.NotAMemberError:
            pass
    header = decorate(mlist, mlist.msg_header, _('non-digest header'), d)
    footer = decorate(mlist, mlist.msg_footer, _('non-digest footer'), d)
    # Be MIME smart here.  We only attach the header and footer by
    # concatenation when the message is a non-multipart of type text/plain.
    # Otherwise, if it is not a multipart, we make it a multipart, and then we
    # add the header and footer as text/plain parts.
    #
    # BJG: In addition, only add the footer if the message's character set
    # matches the charset of the list's preferred language.  This is a
    # suboptimal solution, and should be solved by allowing a list to have
    # multiple headers/footers, for each language the list supports.
    mcset = msg.get_param('charset', 'us-ascii')
    lcset = Utils.GetCharSet(mlist.preferred_language)
    msgtype = msg.get_type('text/plain')
    # BAW: If the charsets don't match, should we add the header and footer by
    # MIME multipart chroming the message?
    if not msg.is_multipart() and msgtype == 'text/plain' and mcset == lcset:
        payload = header + msg.get_payload() + footer
        msg.set_payload(payload)
    elif msg.get_type() == 'multipart/mixed':
        # The next easiest thing to do is just prepend the header and append
        # the footer as additional subparts
        mimehdr = MIMEText(header)
        mimeftr = MIMEText(footer)
        payload = msg.get_payload()
        if not isinstance(payload, ListType):
            payload = [payload]
        payload.append(mimeftr)
        payload.insert(0, mimehdr)
        msg.set_payload(payload, mlist.preferred_language)
    elif msg.get_main_type() <> 'multipart':
        # Okay, we've got some 'image/*' or 'audio/*' -like type.  For now, we
        # simply refuse to add headers and footers to this message.  BAW:
        # still trying to decide what the Right Thing To Do is.
        pass
    else:
        # Now we've got some multipart/* that's not a multipart/mixed.  I'm
        # even less sure about what to do here, so once again, let's not add
        # headers or footers for now.
        pass



def decorate(mlist, template, what, extradict={}):
    # `what' is just a descriptive phrase
    #
    # BAW: We've found too many situations where Python can be fooled into
    # interpolating too much revealing data into a format string.  For
    # example, a footer of "% silly %(real_name)s" would give a header
    # containing all list attributes.  While we've previously removed such
    # really bad ones like `password' and `passwords', it's much better to
    # provide a whitelist of known good attributes, then to try to remove a
    # blacklist of known bad ones.
    d = SafeDict({'real_name'     : mlist.real_name,
                  'list_name'     : mlist.internal_name(),
                  # For backwards compatibility
                  '_internal_name': mlist.internal_name(),
                  'host_name'     : mlist.host_name,
                  'web_page_url'  : mlist.web_page_url,
                  'description'   : mlist.description,
                  'info'          : mlist.info,
                  'cgiext'        : mm_cfg.CGIEXT,
                  })
    d.update(extradict)
    # Using $-strings?
    if getattr(mlist, 'use_dollar_strings', 0):
        template = Utils.to_percent(template)
    # Interpolate into the template
    try:
        text = (template % d).replace('\r\n', '\n')
    except (ValueError, TypeError), e:
        syslog('error', 'Exception while calculating %s:\n%s', what, e)
        what = what.upper()
        text = template
    return text
