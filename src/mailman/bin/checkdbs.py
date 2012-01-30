# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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
import time
import optparse

from email.Charset import Charset

from mailman import MailList
from mailman import Utils
from mailman.app.requests import handle_request
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.initialize import initialize
from mailman.interfaces.requests import IListRequests, RequestType
from mailman.version import MAILMAN_VERSION

# Work around known problems with some RedHat cron daemons
import signal
signal.signal(signal.SIGCHLD, signal.SIG_DFL)

NL = u'\n'
now = time.time()



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Check for pending admin requests and mail the list owners if necessary."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return opts, args, parser



def pending_requests(mlist):
    # Must return a byte string
    lcset = mlist.preferred_language.charset
    pending = []
    first = True
    requestsdb = IListRequests(mlist)
    for request in requestsdb.of_type(RequestType.subscription):
        if first:
            pending.append(_('Pending subscriptions:'))
            first = False
        key, data = requestsdb.get_request(request.id)
        when = data['when']
        addr = data['addr']
        fullname = data['fullname']
        passwd = data['passwd']
        digest = data['digest']
        lang = data['lang']
        if fullname:
            if isinstance(fullname, unicode):
                fullname = fullname.encode(lcset, 'replace')
            fullname = ' (%s)' % fullname
        pending.append('    %s%s %s' % (addr, fullname, time.ctime(when)))
    first = True
    for request in requestsdb.of_type(RequestType.held_message):
        if first:
            pending.append(_('\nPending posts:'))
            first = False
        key, data = requestsdb.get_request(request.id)
        when = data['when']
        sender = data['sender']
        subject = data['subject']
        reason = data['reason']
        text = data['text']
        msgdata = data['msgdata']
        subject = Utils.oneline(subject, lcset)
        date = time.ctime(when)
        reason = _(reason)
        pending.append(_("""\
From: $sender on $date
Subject: $subject
Cause: $reason"""))
        pending.append('')
    # Coerce all items in pending to a Unicode so we can join them
    upending = []
    charset = mlist.preferred_language.charset
    for s in pending:
        if isinstance(s, unicode):
            upending.append(s)
        else:
            upending.append(unicode(s, charset, 'replace'))
    # Make sure that the text we return from here can be encoded to a byte
    # string in the charset of the list's language.  This could fail if for
    # example, the request was pended while the list's language was French,
    # but then it was changed to English before checkdbs ran.
    text = NL.join(upending)
    charset = Charset(mlist.preferred_language.charset)
    incodec = charset.input_codec or 'ascii'
    outcodec = charset.output_codec or 'ascii'
    if isinstance(text, unicode):
        return text.encode(outcodec, 'replace')
    # Be sure this is a byte string encodeable in the list's charset
    utext = unicode(text, incodec, 'replace')
    return utext.encode(outcodec, 'replace')



def auto_discard(mlist):
    # Discard old held messages
    discard_count = 0
    expire = config.days(mlist.max_days_to_hold)
    requestsdb = IListRequests(mlist)
    heldmsgs = list(requestsdb.of_type(RequestType.held_message))
    if expire and heldmsgs:
        for request in heldmsgs:
            key, data = requestsdb.get_request(request.id)
            if now - data['date'] > expire:
                handle_request(mlist, request.id, config.DISCARD)
                discard_count += 1
        mlist.Save()
    return discard_count



# Figure out epoch seconds of midnight at the start of today (or the given
# 3-tuple date of (year, month, day).
def midnight(date=None):
    if date is None:
        date = time.localtime()[:3]
    # -1 for dst flag tells the library to figure it out
    return time.mktime(date + (0,)*5 + (-1,))


def main():
    opts, args, parser = parseargs()
    initialize(opts.config)

    for name in config.list_manager.names:
        # The list must be locked in order to open the requests database
        mlist = MailList.MailList(name)
        try:
            count = IListRequests(mlist).count
            # While we're at it, let's evict yesterday's autoresponse data
            midnight_today = midnight()
            evictions = []
            for sender in mlist.hold_and_cmd_autoresponses.keys():
                date, respcount = mlist.hold_and_cmd_autoresponses[sender]
                if midnight(date) < midnight_today:
                    evictions.append(sender)
            if evictions:
                for sender in evictions:
                    del mlist.hold_and_cmd_autoresponses[sender]
                # This is the only place we've changed the list's database
                mlist.Save()
            if count:
                # Set the default language the the list's preferred language.
                _.default = mlist.preferred_language
                realname = mlist.real_name
                discarded = auto_discard(mlist)
                if discarded:
                    count = count - discarded
                    text = _('Notice: $discarded old request(s) '
                             'automatically expired.\n\n')
                else:
                    text = ''
                if count:
                    text += Utils.maketext(
                        'checkdbs.txt',
                        {'count'    : count,
                         'mail_host': mlist.mail_host,
                         'adminDB'  : mlist.GetScriptURL('admindb',
                                                         absolute=1),
                         'real_name': realname,
                         }, mlist=mlist)
                    text += '\n' + pending_requests(mlist)
                    subject = _('$count $realname moderator '
                                'request(s) waiting')
                else:
                    subject = _('$realname moderator request check result')
                msg = UserNotification(mlist.GetOwnerEmail(),
                                       mlist.GetBouncesEmail(),
                                       subject, text,
                                       mlist.preferred_language)
                msg.send(mlist, **{'tomoderators': True})
        finally:
            mlist.Unlock()



if __name__ == '__main__':
    main()
