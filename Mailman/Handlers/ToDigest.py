# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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

"""Add the message to the list's current digest and possibly send it.

This handler will add the current message to the list's currently accumulating
digest.  If the digest has reached its size threshold, it is delivered by
creating an OutgoingMessage of the digest, setting the `isdigest' attribute,
and injecting it into the pipeline.
"""

import os
import string
import re

from Mailman import Utils
from Mailman import Message
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog

from stat import ST_SIZE
from errno import ENOENT

MIME_SEPARATOR = '__--__--'
MIME_NONSEPARATOR = ' %s ' % MIME_SEPARATOR
EXCLUDE_HEADERS = ('received', 'errors-to')



def process(mlist, msg, msgdata):
    # short circuit non-digestable lists, or for messages that are already
    # digests
    if not mlist.digestable or msgdata.get('isdigest'):
        return
    digestfile = os.path.join(mlist.fullpath(), 'next-digest')
    topicsfile = os.path.join(mlist.fullpath(), 'next-digest-topics')
    omask = os.umask(002)
    try:
        digestfp = open(digestfile, 'a+')
        topicsfp = open(topicsfile, 'a+')
    finally:
        os.umask(omask)
    # For the sender, use either the From: field's name comment or the mail
    # address.  Don't use Sender: field because by now it's been munged into
    # the list-admin's address
    name, addr = msg.getaddr('from')
    sender = quotemime(name or addr)
    # BAW: I don't like using $LANG
    os.environ['LANG'] = mlist.GetPreferredLanguage(sender)
    fromline = quotemime(msg.getheader('from'))
    date = quotemime(msg.getheader('date'))
    body = quotemime(msg.body)
    subject = quotemime(msg.getheader('subject'))
    # don't include the redundant subject prefix in the TOC entries
    mo = re.match('(re:? *)?(%s)' % re.escape(mlist.subject_prefix),
                  subject, re.IGNORECASE)
    if mo:
        subject = subject[:mo.start(2)] + subject[mo.end(2):]
    # Watch for multiline subjects
    slines = []
    for sline in string.split(subject, '\n'):
        if not slines:
            slines.append(sline)
        else:
            slines.append('      ' + sline)
    topicsfp.write('  %2d. %s (%s)\n' % (mlist.next_post_number,
                                         string.join(slines, '\n'),
                                         sender))
    # We exclude specified headers and all X-* headers
    kept_headers = []
    keeping = 0
    have_content_type = 0
    have_content_description = 0
    # speed up the inner loop
    lower, split, excludes = string.lower, string.split, EXCLUDE_HEADERS
    for h in msg.headers:
        if lower(h[:2]) == 'x-' or lower(split(h, ':')[0]) in excludes:
            keeping = 0
        elif h and h[0] in (' ', '\t'):
            if keeping and kept_headers:
                # continuation of something we're keeping
                kept_headers[-1] = kept_headers[-1] + h
        else:
            keeping = 1
            if lower(h[:7]) == 'content-':
                kept_headers.append(h)
                if lower(h[:12]) == 'content-type':
                    have_content_type = 1
                elif lower(h[:19]) == 'content-description':
                    have_content_description = 1
            else:
                kept_headers.append(quotemime(h))
    # after processing the headers
    if have_content_type and not have_content_description:
        kept_headers.append('Content-Description: %s\n' % subject)
    # TBD: reply-to munging happens elsewhere in the pipeline
    digestfp.write('--%s\n\n%s: %d\n%s\n%s' %
                   (MIME_SEPARATOR, _("Message"),  mlist.next_post_number,
                    string.join(kept_headers, ''),
                    body))
    digestfp.write('\n')
    mlist.next_post_number = mlist.next_post_number + 1
    topicsfp.close()
    digestfp.close()
    # if the current digest size exceeds the threshold, send the digest by
    # injection into the list's message pipeline
    try:
        size = os.stat(digestfile)[ST_SIZE]
        if size/1024.0 >= mlist.digest_size_threshhold:
            inject_digest(mlist, digestfile, topicsfile)
    except OSError, e:
        code, msg = e
        if code == ENOENT:
            syslog('error', 'Lost digest file: %s' % digestfile)
            syslog('error', str(e))
    


def inject_digest(mlist, digestfile, topicsfile):
    fp = open(topicsfile, 'r+')
    topicsdata = fp.read()
    fp.close()
    topicscount = string.count(topicsdata, '\n')
    fp = open(digestfile)
    #
    # filters for recipient calculation
    def delivery_enabled_p(x, s=mlist, v=mm_cfg.DisableDelivery):
        return not s.GetUserOption(x, v)
    def likes_mime_p(x, s=mlist, v=mm_cfg.DisableMime):
        return not s.GetUserOption(x, v)
    def hates_mime_p(x, s=mlist, v=mm_cfg.DisableMime):
        return s.GetUserOption(x, v)
    #
    # These people have switched their options from digest delivery to
    # non-digest delivery.  they need to get one last digest, but be sure they
    # haven't switched back to digest delivery in the meantime!
    digestmembers = {}
    if hasattr(mlist, 'one_last_digest'):
        digestmembers.update(mlist.one_last_digest)
        del mlist.one_last_digest
    for addr in mlist.GetDigestMembers():
        digestmembers[addr] = addr
    recipients = filter(delivery_enabled_p, digestmembers.keys())
    mime_recips = filter(likes_mime_p, recipients)
    text_recips = filter(hates_mime_p, recipients)
    #
    # log this digest injection
    syslog('digest',
           '%s v %d - %d msgs, %d recips (%d mime, %d text, %d disabled)' %
           (mlist.real_name, mlist.next_digest_number, topicscount,
            len(digestmembers), len(mime_recips), len(text_recips),
            len(digestmembers) - len(recipients)))
    # do any deliveries
    if mime_recips or text_recips:
        digest = Digest(mlist, topicsdata, fp.read())
        # Generate the MIME digest, but only queue it for delivery so we don't
        # hold the lock too long.
        if mime_recips:
            msg = digest.asMIME()
            msg['To'] = mlist.GetListEmail()
            msg.Enqueue(mlist, recips=mime_recips, isdigest=1, approved=1)
        if text_recips:
            # Generate the RFC934 "plain text" digest, and again, just queue
            # it
            msg = digest.asText()
            msg['To'] = mlist.GetListEmail()
            msg.Enqueue(mlist, recips=text_recips, isdigest=1, approved=1)
    # zap accumulated digest information for the next round
    os.unlink(digestfile)
    os.unlink(topicsfile)
    mlist.next_digest_number = mlist.next_digest_number + 1
    mlist.next_post_number = 1
    syslog('digest', 'next %s digest: #%d, post#%d' %
           (mlist.internal_name(), mlist.next_digest_number,
            mlist.next_post_number))



def quotemime(text):
    # TBD: ug.
    if not text:
        return ''
    return string.join(string.split(text, MIME_SEPARATOR), MIME_NONSEPARATOR)


class Digest:
    """A digest, representable as either a MIME or plain text message."""
    def __init__(self, mlist, toc, body):
        self.__mlist = mlist
        self.__toc = toc
        self.__body = body
        self.__volume = 'Vol %d #%d' % (mlist.volume, mlist.next_digest_number)
        numtopics = string.count(self.__toc, '\n')
        self.__numinfo = '%d msg%s' % (numtopics, numtopics <> 1 and 's' or '')

    def ComposeBaseHeaders(self, msg):
        """Populate the message with the presentation-independent headers."""
        realname = self.__mlist.real_name
        volume = self.__volume
        numinfo = self.__numinfo
	msg['From'] = self.__mlist.GetRequestEmail()
	msg['Subject'] = _('%(realname)s digest, %(volume)s - %(numinfo)s')
	msg['Reply-to'] = self.__mlist.GetListEmail()
        msg['X-Mailer'] = "Mailman v%s" % mm_cfg.VERSION
        msg['MIME-version'] = '1.0'

    def TemplateRefs(self):
        """Resolve references in a format string against list settings.

        The resolution is done against a copy of the lists attribute
        dictionary, with the addition of some of settings for computed
        items - got_listinfo_url, got_request_email, got_list_email, and
        got_owner_email.

        """
        # Collect the substitutions:
        if hasattr(self, 'substitutions'):
            return Utils.SafeDict(self.substitutions)
        mlist = self.__mlist
        substs = Utils.SafeDict()
        substs.update(mlist.__dict__)
        substs.update(
            {'got_listinfo_url' : mlist.GetScriptURL('listinfo', absolute=1),
             'got_request_email': mlist.GetRequestEmail(),
             'got_list_email'   : mlist.GetListEmail(),
             'got_owner_email'  : mlist.GetAdminEmail(),
             'cgiext'           : mm_cfg.CGIEXT,
             })
        return substs

    def asMIME(self):
        return self.Present(mime=1)

    def asText(self):
        return self.Present(mime=0)

    def Present(self, mime):
        """Produce a rendering of the digest, as an OutgoingMessage."""
        msg = Message.OutgoingMessage()
        self.ComposeBaseHeaders(msg)
        digestboundary = MIME_SEPARATOR
        if mime:
            import mimetools
            envboundary = mimetools.choose_boundary()
            msg['Content-type'] = 'multipart/mixed; boundary=' + envboundary
        else:
            envboundary = MIME_SEPARATOR
            msg['Content-type'] = 'text/plain'
        dashbound = "--" + envboundary
        # holds lines of the message
        lines = []
        # Masthead:
        if mime:
            realname = self.__mlist.real_name
            volume = self.__volume
            lines.append(dashbound)
            lines.append("Content-type: text/plain; charset=" + Utils.GetCharSet())
            lines.append("Content-description:" +
                         _(" Masthead (%(realname)s digest, %(volume)s)"))
            lines.append('')
        masthead = Utils.maketext('masthead.txt', self.TemplateRefs(), 
                                                      self.__mlist.preferred_language)
        lines = lines + string.split(masthead, '\n')
        # List-specific header:
        if self.__mlist.digest_header:
            lines.append('')
            if mime:
                lines.append(dashbound)
                lines.append("Content-type: text/plain; charset=" + Utils.GetCharSet())
                lines.append("Content-description: " + _("Digest Header"))
                lines.append('')
            lines.append(self.__mlist.digest_header % self.TemplateRefs())
        # Table of contents:
        lines.append('')
        if mime:
            numinfo = self.__numinfo
            lines.append(dashbound)
            lines.append("Content-type: text/plain; charset=" + Utils.GetCharSet())
            lines.append("Content-description: " +
                         _("Today's Topics (%(numinfo)s)"))
            lines.append('')
        lines.append(_("Today's Topics:"))
        lines.append('')
        lines.append(self.__toc)
        # Digest text:
        if mime:
            lines.append(dashbound)
            lines.append('Content-type: multipart/digest; boundary="%s"'
                         % digestboundary)
            lines.append('')
            lines.append(self.__body)
            # End multipart digest text part
            lines.append('')
            lines.append("--" + digestboundary + "--")
        else:
            lines.extend(filter_headers(
                self.__body,
                mm_cfg.DEFAULT_PLAIN_DIGEST_KEEP_HEADERS,
                digestboundary))
        # List-specific footer:
        if self.__mlist.digest_footer:
            lines.append(dashbound)
            if mime:
                lines.append("Content-type: text/plain; charset=" + Utils.GetCharSet())
                lines.append("Content-description: " + _("Digest Footer"))
            lines.append('')
            lines.append(self.__mlist.digest_footer % self.TemplateRefs())
        # Close:
        if mime:
            # Close encompassing mime envelope.
            lines.append('')
            lines.append(dashbound + "--")
        lines.append('')
        realname = self.__mlist.real_name
        lines.append(_("End of %(realname)s Digest"))
        msg.body = string.join(lines, '\n')
        return msg



def filter_headers(body, keep_headers, mimesep):
    """Return copy of body that omits non-crucial headers."""
    SEPARATOR = 0
    HEADER = 1
    BODY = 2
    # simple state machine
    state = SEPARATOR
    lines = string.split(body, '\n')
    lineno = 1
    text = [lines[0]]
    keptlast = 0
    for lineno in range(1, len(lines)):
        line = lines[lineno]
        if state == BODY:
            # Snarf the body up to, and including, the next separator
            text.append(line)
            if string.strip(line) == '--' + mimesep:
                state = SEPARATOR
            continue
        elif state == SEPARATOR:
            state = HEADER
            # Keep the one (blank) line between separator and headers
            text.append(line)
            keptlast = 0
            continue
        elif state == HEADER:
            if not string.strip(line):
                state = BODY
                text.append(line)
                continue
            elif line[0] in (' ', '\t'):
                # Continuation line, keep if the prior line was kept
                if keptlast:
                    text.append(line)
                continue
            else:
                i = string.find(line, ':')
                if i < 0:
                    # Malformed header line.  Interesting, keep it.
                    text.append(line)
                    keptlast = 1
                else:
                    field = line[:i]
                    if string.lower(field) in keep_headers:
                        text.append(line)
                        keptlast = 1
                    else:
                        keptlast = 0
    return text
