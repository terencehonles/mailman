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

"""Inject the message to Usenet."""

import os
import string
import re

from Mailman.pythonlib.StringIO import StringIO



def process(mlist, msg):
    # short circuits
    if not mlist.gateway_to_news or \
            getattr(msg, 'isdigest', 0) or \
            getattr(msg, 'fromusenet', 0):
        # then
        return
    # sanity checks
    error = []
    if not mlist.linked_newsgroup:
        error.append('no newsgroup')
    if not mlist.nntp_host:
        error.append('no NNTP host')
    if error:
        msg = 'NNTP gateway improperly configured: ' + string.join(error, ', ')
        mlist.LogMsg('error', msg)
        return
    # Fork in case the nntp connection hangs.
    pid = os.fork()
    if not pid:
        do_child(mlist, msg)
    # TBD: we probably want to reap all those children, but do it in a way
    # that doesn't keep the MailList object locked.  Problem is that we don't
    # know what other handlers are going to execute.  Handling children should
    # be pushed up into a higher module
        


def do_child(mlist, msg):
    # child
    import nntplib
    # Ok, munge headers, etc.
    subj = msg.getheader('subject')
    if subj:
        subjpref = mlist.subject_prefix
        if not re.match('(re:? *)?' + re.escape(subjpref), subj, re.I):
            msg['Subject'] = subjpref + subj
    else:
        msg['Subject'] = subjpref + '(no subject)'
    if mlist.reply_goes_to_list:
        del msg['reply-to']
        msg.headers.append('Reply-To: %s\n' % mlist.GetListEmail())
    # if we already have a sender header, don't add another one; use
    # the header that's already there.
    if not msg.getheader('sender'):
        msg.headers.append('Sender: %s\n' % mlist.GetAdminEmail())
    msg.headers.append('Errors-To: %s\n' % mlist.GetAdminEmail())
    msg.headers.append('X-BeenThere: %s\n' % mlist.GetListEmail())
    ngheader = msg.getheader('newsgroups')
    if ngheader is not None:
        # see if the Newsgroups: header already contains our
        # linked_newsgroup.  If so, don't add it again.  If not,
        # append our linked_newsgroup to the end of the header list
        ngroups = map(string.strip, string.split(ngheader, ','))
        if mlist.linked_newsgroup not in ngroups:
            ngroups.append(mlist.linked_newsgroup)
            ngheader = string.join(ngroups, ',')
            # subtitute our new header for the old one.  XXX Message
            # class should have a __setitem__()
            del msg['newsgroups']
            msg.headers.append('Newsgroups: %s\n' % ngroups)
    else:
        # Newsgroups: isn't in the message
        msg.headers.append('Newsgroups: %s\n' % mlist.linked_newsgroup)
    # Note: Need to be sure 2 messages aren't ever sent to the same
    # list in the same process, since message ID's need to be unique.
    # Could make the ID be mm.listname.postnum instead if that happens
    if msg.getheader('Message-ID') is None:
        msg.headers.append('Message-ID: <mm.%s.%s@%s>\n' %
                           (time.time(), os.getpid(), mlist.host_name))
    if msg.getheader('Lines') is None:
        msg.headers.append('Lines: %s\n' % 
                           len(string.split(msg.body,"\n")))
    del msg['received']
    # TBD: Gross hack to ensure that we have only one
    # content-transfer-encoding header.  More than one barfs NNTP.  I
    # don't know why we sometimes have more than one such header, and it
    # probably isn't correct to take the value of just the first one.
    # What if there are conflicting headers???
    #
    # This relies on the new interface for getaddrlist() returning values
    # for all present headers, and the fact that the legal values are
    # usually not parseable as addresses.  Yes this is another bogosity.
    cteheaders = msg.getaddrlist('content-transfer-encoding')
    if cteheaders:
        ctetuple = cteheaders[0]
        ctevalue = ctetuple[1]
        del msg['content-transfer-encoding']
        msg['content-transfer-encoding'] = ctevalue
    # NNTP is strict about spaces after the colon in headers.
    for n in range(len(msg.headers)):
        line = msg.headers[n]
        i = string.find(line,":")
        if i <> -1 and line[i+1] <> ' ':
            msg.headers[n] = line[:i+1] + ' ' + line[i+1:]
    # flatten the message object, stick it in a StringIO object and post
    # that resulting thing to the newsgroup
    fp = StringIO(str(msg))
    conn = nntplib.NNTP(mlist.nntp_host)
    try:
        try:
            conn.post(fp)
        except nntplib.error_temp, e:
            sys.stderr.write('encountered NNTP error for list %s\n' %
                             mlist.internal_name())
            sys.stderr.write(str(e) + '\n')
    finally:
        conn.quit()
    os._exit(0)
