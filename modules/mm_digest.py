"""Mixin class with list-digest handling methods and settings."""

__version__ = "$Revision: 455 $"

import mm_utils, mm_err, mm_message, mm_cfg
import time, os, string

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
	digest_file.write("--%s\n\nMessage: %d"
			  "\nFrom: %s\nDate: %s\nSubject: %s\n\n%s" % 
			 (self._mime_separator, self.next_post_number,
			  fromline, date, subject,
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
	msg = mm_message.OutgoingMessage()
	msg.SetSender(self.GetAdminEmail())
	msg.SetHeader('Subject', '%s digest, Volume %d #%d' % 
		       (self.real_name, self.volume, self.next_digest_number))
	msg.SetHeader('mime-version', '1.0')
	msg.SetHeader('content-type', 'multipart/digest; boundary="%s"' % 
		       self._mime_separator)
	msg.SetHeader('reply-to', self.GetListEmail())

        digest_file = open(os.path.join(self._full_path, 'next-digest'), 'r+')
	msg.SetBody(digest_file.read())

	# Create the header and footer... a bit messy.
	topics_file = open(os.path.join(self._full_path,
					'next-digest-topics'), 
			   'r+')
	topics_text = topics_file.read()
        topics_number = string.count(topics_text, '\n')

        subst = {}
        for k, v in self.__dict__.items():
            subst[k] = v
        subst['_mime_separator'] = self._mime_separator
        subst.update({'got_sender': msg.GetSender(),
                      'got_listinfo_url': self.GetScriptURL('listinfo'),
                      'got_request_email': self.GetRequestEmail(),
                      'got_date':         time.ctime(time.time()),
                      'got_list_email': self.GetListEmail(),
                      'got_topics_text': topics_text})

	digest_header = '''--%(_mime_separator)s

From: %(got_sender)s
Subject: Contents of %(real_name)s digest, Volume %(volume)d #%(next_digest_number)d
Date: %(got_date)s

Send %(real_name)s maillist submissions to
	%(got_list_email)s

To subscribe or unsubscribe via the web, visit
	%(got_listinfo_url)s
or send email to %(got_request_email)s

(When replying, please edit your Subject line so it is more specific than
"Re: Contents of %(real_name)s digest...")

Topics for this digest:
%(got_topics_text)s
''' %   subst

        if self.digest_header:
	    digest_header = digest_header + (self.digest_header
					     % self.__dict__)
	if self.digest_footer:
            subst['got_footer'] = self.digest_footer % self.__dict__

	    digest_footer = '''--%(_mime_separator)s

From: %(got_sender)s
Subject: %(real_name)s V%(volume)s#%(next_digest_number)s Digest Footer
Date: %(got_date)s

%(got_footer)s
--%(_mime_separator)s--''' % subst
        else:
	    digest_footer = '''
--%s--''' % self._mime_separator


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
	self.DeliverToList(msg, mime_recipients, digest_header, 
	                   digest_footer, remove_to=1,
			   tmpfile_prefix = "mime.")
	msg.SetHeader('content-type', 'text/plain', crush_duplicates=1)

        # Zero the digest files only *just* before the messages are out.
	topics_file.truncate(0)
	topics_file.close()
	digest_file.truncate(0)
	digest_file.close()

	self.DeliverToList(msg, text_recipients, digest_header,
			   digest_footer, remove_to=1)

	self.next_digest_number = self.next_digest_number + 1
	self.next_post_number = 1
	self.Save()
