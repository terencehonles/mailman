"""Mixin class with list-digest handling methods and settings."""

__version__ = "$Revision: 500 $"

import mm_utils, mm_err, mm_message, mm_cfg
import time, os, string, re

DIGEST_MASTHEAD = """
Send %(real_name)s maillist submissions to
	%(got_list_email)s

To subscribe or unsubscribe via the web, visit
	%(got_listinfo_url)s
or, via email, send a message with subject or body 'help' to
	%(got_request_email)s
You can reach the person managing the list at
	%(got_owner_email)s

(When replying, please edit your Subject line so it is more specific than
"Re: Contents of %(real_name)s digest...")
"""


class Digester:
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
	self.digest_members = []
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

	    ('digest_send_periodic', mm_cfg.Number, 3, 0,
	     'Should a digest be dispatched daily when the size threshold '
	     "isn't reached?"),

	    ('digest_header', mm_cfg.Text, (4, 55), 0,
	     'Header added to every digest',
             "Text attached (as an initial message, before the table"
             " of contents) to the top of digests.<p>"
             + mm_err.MESSAGE_DECORATION_NOTE),

	    ('digest_footer', mm_cfg.Text, (4, 55), 0,
	     'Footer added to every digest',
             "Text attached (as a final message) to the bottom of digests.<p>"
             + mm_err.MESSAGE_DECORATION_NOTE),
	    ]

    def SetUserDigest(self, sender, value):
	self.IsListInitialized()
	addr = self.FindUser(sender)
	if not addr:
	    raise mm_err.MMNotAMemberError
	if addr in self.members:
	    if value == 0:
		raise mm_err.MMAlreadyUndigested
	    else:
		if not self.digestable:
		    raise mm_err.MMCantDigestError
		self.members.remove(addr)
		self.digest_members.append(addr)
	else:
	    if value == 1:
		raise mm_err.MMAlreadyDigested
	    else:
		if not self.nondigestable:
		    raise mm_err.MMMustDigestError
		self.digest_members.remove(addr)
		self.members.append(addr)
	self.Save()


# Internal function, don't call this.
    def SaveForDigest(self, post):
	"""Add message to index, and to the digest.  If the digest is large
	enough when we're done writing, send it out."""
	digest_file = open(os.path.join(self._full_path, "next-digest"),
			   "a+")
	topics_file = open(os.path.join(self._full_path,
					"next-digest-topics"), 
			   "a+")
	sender = self.QuoteMime(post.GetSenderName())
	fromline = self.QuoteMime(post.getheader("from"))
	subject = self.QuoteMime(post.getheader("subject"))
	date = self.QuoteMime(post.getheader("date"))
	body = self.QuoteMime(post.body)
	topics_file.write("  %d. %s (%s)\n" % (self.next_post_number,
					       subject, sender))
        if self.reply_goes_to_list:
            maybe_replyto=('Reply-To: %s\n'
                           % self.QuoteMime(self.GetListEmail()))
        else:
            maybe_replyto=''            
        digest_file.write("--%s\n\nMessage: %d"
                          "\nFrom: %s\nDate: %s\nSubject: %s\n%s\n%s" % 
                          (self._mime_separator, self.next_post_number,
                           fromline, date, subject, maybe_replyto,
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

	recipients = filter(DeliveryEnabled, self.digest_members)
	mime_recipients = filter(LikesMime, recipients)
	text_recipients = filter(HatesMime, recipients)
	self.LogMsg("digest",
		    'Fake %s digest %d log--',
		    self.real_name, self.next_digest_number)
	self.LogMsg("digest",
		    ('Fake %d digesters, %d disabled.  '
		     'Active: %d MIMEers, %d non.'),
		    len(self.digest_members),
		    len(self.digest_members) - len(recipients),
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
	recipients = filter(DeliveryEnabled, self.digest_members)
	mime_recipients = filter(LikesMime, recipients)
	text_recipients = filter(HatesMime, recipients)

        self.LogMsg("digest",
                    ('%s v %d - '
                     '%d msgs %d dgstrs: %d m %d non %d dis'),
                    self.real_name,
                    self.next_digest_number,
                    topics_number,
                    len(self.digest_members),
                    len(mime_recipients),
                    len(text_recipients),
                    len(self.digest_members) - len(recipients))

        if mime_recipients or text_recipients:
            d = Digest(self, topics_text, digest_text)
        else:
            d = None

        # Zero the digest files only just before the messages go out.
        topics_file.truncate(0)
        topics_file.close()
        digest_file.truncate(0)
        digest_file.close()
	self.next_digest_number = self.next_digest_number + 1
	self.next_post_number = 1
	self.Save()

        if text_recipients:
            self.DeliverToList(d.Present(mime=0),
                               text_recipients, remove_to=1)
        if mime_recipients:
            self.DeliverToList(d.Present(mime=1),
                               mime_recipients,
                               remove_to=1, tmpfile_prefix = "mime.")

class Digest:
    "Represent a maillist digest, presentable in either plain or mime format."
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
            substs.update({'got_listinfo_url': lst.GetScriptURL('listinfo'),
                           'got_request_email': lst.GetRequestEmail(),
                           'got_list_email': lst.GetListEmail(),
                           'got_owner_email': lst.GetAdminEmail(),
                           })
        return text % substs

    def Present(self, mime=0):
        """Produce a rendering of the digest, as an OutgoingMessage."""
        msg = mm_message.OutgoingMessage()
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
            lines.append("Content-description: Masthead (%s digest, Vol %s)"
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
        lines.append("")
        lines.append("--" + digestboundary + "--")
        if mime:
            # Close encompassing mime envelope.
            lines.append("")
            lines.append(dashbound + "--")
        lines.append("")
        lines.append("End of %s Digest" % self.list.real_name)

        msg.SetBody(string.join(lines, "\n"))
        return msg
