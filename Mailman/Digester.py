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


"""Mixin class with list-digest handling methods and settings."""

import os
import string
import time
import re
import Errors
import Message
import mm_cfg


# See templates/masthead.txt
# XXX: this needs conversion
DIGEST_MASTHEAD = """
Send %(real_name)s mailing list submissions to
	%(got_list_email)s

To subscribe or unsubscribe via the web, visit
	%(got_listinfo_url)s
or, via email, send a message with subject or body 'help' to
	%(got_request_email)s
You can reach the person managing the list at
	%(got_owner_email)s

When replying, please edit your Subject line so it is more specific than
"Re: Contents of %(real_name)s digest..."
"""


class Digester:
    def InitTempVars(self):
	self._mime_separator = '__--__--' 
        
    def InitVars(self):
	# Configurable
	self.digestable = mm_cfg.DEFAULT_DIGESTABLE
	self.digest_is_default = mm_cfg.DEFAULT_DIGEST_IS_DEFAULT
	self.mime_is_default_digest = mm_cfg.DEFAULT_MIME_IS_DEFAULT_DIGEST
	self.digest_size_threshhold = mm_cfg.DEFAULT_DIGEST_SIZE_THRESHHOLD
	self.digest_send_periodic = mm_cfg.DEFAULT_DIGEST_SEND_PERIODIC
	self.next_post_number = 1
	self.digest_header = mm_cfg.DEFAULT_DIGEST_HEADER
	self.digest_footer = mm_cfg.DEFAULT_DIGEST_FOOTER
	
	# Non-configurable.
	self.digest_members = {}
	self.next_digest_number = 1

    def GetConfigInfo(self):
	return [
            "Batched-delivery digest characteristics.",

	    ('digestable', mm_cfg.Toggle, ('No', 'Yes'), 1,
	     'Can list members choose to receive list traffic '
	     'bunched in digests?'),

	    ('digest_is_default', mm_cfg.Radio, 
	     ('Regular', 'Digest'), 0,
	     'Which delivery mode is the default for new users?'),

	    ('mime_is_default_digest', mm_cfg.Radio, 
	     ('Plain', 'Mime'), 0,
	     'When receiving digests, which format is default?'),

	    ('digest_size_threshhold', mm_cfg.Number, 3, 0,
	     'How big in Kb should a digest be before it gets sent out?'),
            # Should offer a 'set to 0' for no size threshhold.

 	    ('digest_send_periodic', mm_cfg.Radio, ('No', 'Yes'), 1,
	     'Should a digest be dispatched daily when the size threshold '
	     "isn't reached?"),

            ('digest_header', mm_cfg.Text, (4, 55), 0,
	     'Header added to every digest',
             "Text attached (as an initial message, before the table"
             " of contents) to the top of digests.<p>"
             + Errors.MESSAGE_DECORATION_NOTE),

	    ('digest_footer', mm_cfg.Text, (4, 55), 0,
	     'Footer added to every digest',
             "Text attached (as a final message) to the bottom of digests.<p>"
             + Errors.MESSAGE_DECORATION_NOTE),
	    ]

    def SetUserDigest(self, sender, value):
	self.IsListInitialized()
	addr = self.FindUser(sender)
	if not addr:
	    raise Errors.MMNotAMemberError
        cpuser = self.GetUserSubscribedAddress(addr)
	if self.members.has_key(addr):
	    if value == 0:
		raise Errors.MMAlreadyUndigested
	    else:
		if not self.digestable:
		    raise Errors.MMCantDigestError
		del self.members[addr]
		self.digest_members[addr] = cpuser
	else:
	    if value == 1:
		raise Errors.MMAlreadyDigested
	    else:
		if not self.nondigestable:
		    raise Errors.MMMustDigestError
                try:
                    self.one_last_digest[addr] = self.digest_members[addr]
                except AttributeError:
                    self.one_last_digest = {addr: self.digest_members[addr]}
		del self.digest_members[addr]
		self.members[addr] = cpuser
	self.Save()

    # Internal function, don't call this.
    def SaveForDigest(self, post):
	"""Add message to index, and to the digest.  If the digest is large
	enough when we're done writing, send it out."""
	ou = os.umask(002)
	try:
            digest_file = open(os.path.join(self._full_path, "next-digest"),
                               "a+")
            topics_file = open(os.path.join(self._full_path,
                                            "next-digest-topics"), 
                               "a+")
	finally:
	    os.umask(ou)
	sender = self.QuoteMime(post.GetSenderName())
	fromline = self.QuoteMime(post.getheader("from"))
	date = self.QuoteMime(post.getheader("date"))
	body = self.QuoteMime(post.body)
	subject = self.QuoteMime(post.getheader("subject"))
        # Don't include the redundant subject prefix in the toc entries:
        matched = re.match("(re:? *)?(%s)" % re.escape(self.subject_prefix),
                           subject, re.I)
        if matched:
            subject = subject[:matched.start(2)] + subject[matched.end(2):]
	topics_file.write("  %d. %s (%s)\n" % (self.next_post_number,
					       subject, sender))
        # We exclude specified headers *and* all "X-*" headers.
        exclude_headers = ['received', 'errors-to']
        kept_headers = []
        keeping = 0
        have_content_type = 0
        have_content_description = 0
        lower, split = string.lower, string.split
        for h in post.headers:
            if (lower(h[:2]) == "x-"
                or lower(split(h, ':')[0]) in exclude_headers):
                keeping = 0
            elif (h and h[0] in [" ", "\t"]):
                if (keeping and kept_headers):
                    # Continuation of something we're keeping.
                    kept_headers[-1] = kept_headers[-1] + h
            else:
                keeping = 1
                if lower(h[:7]) == "content-":
                    kept_headers.append(h)
                    if lower(h[:12]) == "content-type":
                        have_content_type = 1
                    if lower(h[:19]) == "content-description":
                        have_content_description = 1
                else:
                    kept_headers.append(self.QuoteMime(h))
        if (have_content_type and not have_content_description):
            kept_headers.append("Content-Description: %s\n" % subject)
        if self.reply_goes_to_list:
            # Munge the reply-to - sigh.
            kept_headers.append('Reply-To: %s\n'
                                % self.QuoteMime(self.GetListEmail()))

        # Do the save.
        digest_file.write("--%s\n\nMessage: %d\n%s\n%s"
                          % (self._mime_separator, self.next_post_number,
                             string.join(kept_headers, ""),
                             body))
	self.next_post_number = self.next_post_number + 1
	topics_file.close()
	digest_file.close()    
	self.SendDigestOnSize(self.digest_size_threshhold)

    def SendDigestIfAny(self):
	"""Send the digest if there are any messages pending."""
	self.SendDigestOnSize(0)

    def SendDigestOnSize(self, threshhold):
	"""Call SendDigest if accumulated digest exceeds threshhold.

	(There must be some content, even if threshhold is 0.)"""
	try:
	    ndf = os.path.join(self._full_path, "next-digest")
	    size = os.stat(ndf)[6]
	    if size == 0:
		return
	    elif (size/1024.) >= threshhold:
		self.SendDigest()
	except os.error, err:
	    if err[0] == 2:
		# No such file or directory
		self.LogMsg("error", "mm_digest lost digest file %s, %s",
			    ndf, err)

# If the mime separator appears in the text anywhere, throw a space on
# both sides of it, so it doesn't get interpreted as a real mime separator.
    def QuoteMime(self, text):
	if not text:
	    return text
	return string.join(string.split(text, self._mime_separator), ' %s ' %
			   self._mime_separator)

    def FakeDigest(self):
	def DeliveryEnabled(x, s=self, v=mm_cfg.DisableDelivery):
	    return not s.GetUserOption(x, v)

	def LikesMime(x, s=self, v=mm_cfg.DisableMime):
	    return not s.GetUserOption(x, v)

	def HatesMime(x, s=self, v=mm_cfg.DisableMime):
	    return s.GetUserOption(x, v)

        digestmembers = self.GetDigestDeliveryMembers()
	recipients = filter(DeliveryEnabled, digestmembers)
	mime_recipients = filter(LikesMime, recipients)
	text_recipients = filter(HatesMime, recipients)
	self.LogMsg("digest",
		    'Fake %s digest %d log--',
		    self.real_name, self.next_digest_number)
	self.LogMsg("digest",
		    ('Fake %d digesters, %d disabled.  '
		     'Active: %d MIMEers, %d non.'),
		    len(digestmembers),
		    len(digestmembers) - len(recipients),
		    len(mime_recipients), len(text_recipients))

    def SendDigest(self):
	topics_file = open(os.path.join(self._full_path, 'next-digest-topics'),
			   'r+')
	topics_text = topics_file.read()
        topics_number = string.count(topics_text, '\n')
        topics_plural = ((topics_number != 1) and "s") or ""
        digest_file = open(os.path.join(self._full_path, 'next-digest'), 'r+')

	def DeliveryEnabled(x, s=self, v=mm_cfg.DisableDelivery):
	    return not s.GetUserOption(x, v)
	def LikesMime(x, s=self, v=mm_cfg.DisableMime):
	    return not s.GetUserOption(x, v)
	def HatesMime(x, s=self, v=mm_cfg.DisableMime):
	    return s.GetUserOption(x, v)
        try:
            final_digesters = self.one_last_digest.keys()
        except AttributeError:
            final_digesters = []
        digestmembers = self.GetDigestMembers() + final_digesters
	recipients = filter(DeliveryEnabled, digestmembers)
	mime_recipients = filter(LikesMime, recipients)
	text_recipients = filter(HatesMime, recipients)
        
        self.LogMsg("digest",
                    ('%s v %d - '
                     '%d msgs %d dgstrs: %d m %d non %d dis'),
                    self.real_name,
                    self.next_digest_number,
                    topics_number,
                    len(digestmembers),
                    len(mime_recipients),
                    len(text_recipients),
                    len(digestmembers) - len(recipients))
        if mime_recipients or text_recipients:
            d = Digest(self, topics_text, digest_file.read())
        else:
            d = None
        # Zero the digest files only just before the messages go out.
        topics_file.truncate(0)
        topics_file.close()
        digest_file.truncate(0)
        digest_file.close()
	self.next_digest_number = self.next_digest_number + 1
	self.next_post_number = 1
        # these folks already got their last digest
        self.one_last_digest = {}
	self.Save()

        if text_recipients:
            self.DeliverToList(d.Present(mime=0), 
                               text_recipients, remove_to=1)
        if mime_recipients:
            self.DeliverToList(d.Present(mime=1), 
                               mime_recipients,
                               remove_to=1, tmpfile_prefix = "mime.")

class Digest:
    "Represent a list digest, presentable in either plain or mime format."
    def __init__(self, list, toc, body):
        self.list = list
        self.toc = toc
        self.body = body
        self.baseheaders = []
        self.volinfo = "Vol %d #%d" % (list.volume, list.next_digest_number)
        numtopics = string.count(self.toc, '\n')
        plural = ((numtopics != 1) and "s") or ""
        self.numinfo = "%d msg%s" % (numtopics, plural)

    def ComposeBaseHeaders(self, msg):
        """Populate the message with the presentation-independent headers."""
        lst = self.list
	msg.SetSender(lst.GetAdminEmail())
	msg.SetHeader('Subject',
                      ('%s digest, %s - %s' % 
                       (lst.real_name, self.volinfo, self.numinfo)))
	msg.SetHeader('Reply-to', lst.GetListEmail())
        msg.SetHeader('X-Mailer', "Mailman v%s" % mm_cfg.VERSION)
        msg.SetHeader('MIME-version', '1.0')

    def SatisfyRefs(self, text):
        """Resolve references in a format string against list settings.

        The resolution is done against a copy of the lists attribute
        dictionary, with the addition of some of settings for computed
        items - got_listinfo_url, got_request_email, got_list_email, and
        got_owner_email."""
        # Collect the substitutions:
        if hasattr(self, 'substitutions'):
            substs = self.substitutions
        else:
            lst = self.list
            substs = {}
            substs.update(lst.__dict__)
            substs.update({'got_listinfo_url': 
                                        lst.GetAbsoluteScriptURL('listinfo'),
                           'got_request_email': lst.GetRequestEmail(),
                           'got_list_email': lst.GetListEmail(),
                           'got_owner_email': lst.GetAdminEmail(),
                           })
        return text % substs

    def Present(self, mime=0):
        """Produce a rendering of the digest, as an OutgoingMessage."""
        msg = Message.OutgoingMessage()
        self.ComposeBaseHeaders(msg)
        digestboundary = self.list._mime_separator
        if mime:
            import mimetools
            envboundary = mimetools.choose_boundary()
            msg.SetHeader('Content-type',
                          'multipart/mixed; boundary="%s"' % envboundary)
        else:
            envboundary = self.list._mime_separator
            msg.SetHeader('Content-type', 'text/plain')
        dashbound = "--" + envboundary

        lines = []

        # Masthead:
        if mime:
            lines.append(dashbound)
            lines.append("Content-type: text/plain; charset=us-ascii")
            lines.append("Content-description: Masthead (%s digest, %s)"
                         % (self.list.real_name, self.volinfo))
        lines.append(self.SatisfyRefs(DIGEST_MASTHEAD))
        
        # List-specific header:
        if self.list.digest_header:
            lines.append("")
            if mime:
                lines.append(dashbound)
                lines.append("Content-type: text/plain; charset=us-ascii")
                lines.append("Content-description: Digest Header")
                lines.append("")
            lines.append(self.SatisfyRefs(self.list.digest_header))

        # Table of contents:
        lines.append("")
        if mime:
            lines.append(dashbound)
            lines.append("Content-type: text/plain; charset=us-ascii")
            lines.append("Content-description: Today's Topics (%s)" %
                         self.numinfo)
            lines.append("")
        lines.append("Today's Topics:")
        lines.append("")
        lines.append(self.toc)

        # Digest text:
        if mime:
            lines.append(dashbound)
            lines.append('Content-type: multipart/digest; boundary="%s"'
                         % digestboundary)
            lines.append("")
            lines.append(self.body)
            # End multipart digest text part
            lines.append("")
            lines.append("--" + digestboundary + "--")
        else:
            lines.append(
                filterDigestHeaders(self.body,
                                    mm_cfg.DEFAULT_PLAIN_DIGEST_KEEP_HEADERS,
                                    digestboundary))
        # List-specific footer:
        if self.list.digest_footer:
            lines.append("")
            lines.append(dashbound)
            if mime:
                lines.append("Content-type: text/plain; charset=us-ascii")
                lines.append("Content-description: Digest Footer")
            lines.append("")
            lines.append(self.SatisfyRefs(self.list.digest_footer))

        # Close:
        if mime:
            # Close encompassing mime envelope.
            lines.append("")
            lines.append(dashbound + "--")
        lines.append("")
        lines.append("End of %s Digest" % self.list.real_name)

        msg.SetBody(string.join(lines, "\n"))
        return msg

def filterDigestHeaders(body, keep_headers, mimesep):
    """Return copy of body that omits non-crucial headers."""
    state = "sep"               # "sep", "head", or "body"
    lines = string.split(body, "\n")
    at = 1
    text = [lines[0]]
    kept_last = 0
    while at < len(lines):
        l, at = lines[at], at + 1
        if state == "body":
            # Snarf the body up to, and including, the next separator:
            text.append(l)
            if string.strip(l) == '--' + mimesep:
                state = "sep"
            continue
        elif state == "sep":
            state = "head"
            # Keep the one (blank) line between separator and headers.
            text.append(l)
            kept_last = 0
            continue
        elif state == "head":
            l = string.strip(l)
            if l == '':
                state = "body"
                text.append(l)
                continue
            elif l[0] in [' ', '\t']:
                # Continuation line - keep if the prior line was kept.
                if kept_last:
                    text.append(l)
                continue
            else:
                where = string.find(l, ':')
                if where == -1:
                    # Malformed header line - interesting, keep it.
                    text.append(l)
                    kept_last = 1
                else:
                    field = l[:where]
                    if string.lower(field) in keep_headers:
                        text.append(l)
                        kept_last = 1
                    else:
                        kept_last = 0
    return string.join(text, '\n')
