import mm_utils, mm_err, mm_message, mm_cfg
import time, os, string

class Digester:
    def InitVars(self):
	# Configurable
	self.digest_header = None
	self.digest_footer = None
	self.digestable = 1
	self.digest_is_default = 0
	self.digest_size_threshhold = 30 # In K
	self.next_post_number = 1
	
	# Non-configurable.
	self.digest_members = []
	self.next_digest_number = 1

    def GetConfigInfo(self):
	return [

	    ('digestable', mm_cfg.Toggle, ('No', 'Yes'), 1,
	     'Can members choose to receive digests instead of '
	     'individual pieces of mail?'),

	    ('digest_size_threshhold', mm_cfg.Number, 3, 0,
	     'How big in Kb should a digest be before it gets sent out?'),

	    ('digest_header', mm_cfg.Text, (4, 65), 0,
	     'Header added to every digest'),

	    ('digest_footer', mm_cfg.Text, (4, 65), 0,
	     'Footer added to every digest'),

	    ('digest_is_default', mm_cfg.Radio, 
	     ('Regular mail', 'Digests'), 0,
	     'If one doesn\'t specify a preference, '
	     '(s)he gets what by default?')
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
	# Add message to index, and to the digest.
	# If the digest is large enough when we're done writing, send it out.
	digest_file = open(os.path.join(self._full_path, "next-digest"), "a+")
	topics_file = open(os.path.join(self._full_path, "next-digest-topics"), 
			   "a+")
	sender = self.QuoteMime(post.GetSenderName())
	fromline = self.QuoteMime(post.getheader("from"))
	subject = self.QuoteMime(post.getheader("subject"))
	date = self.QuoteMime(post.getheader("date"))
	body = self.QuoteMime(post.body)
	topics_file.write("  %d. %s (%s)\n" % (self.next_post_number,
					       subject, sender))
	digest_file.write("--%s\n\nFrom: %s\nDate: %s\nSubject: %s\n\n" % 
			 (self._mime_separator, fromline, date, subject))
	digest_file.write("** Message %d: **\n\n%s\n" % 
			  (self.next_post_number, body))
	digest_file.write("** End of message %d from %s **\n" % 
			  (self.next_post_number, fromline))
	self.next_post_number = self.next_post_number + 1
	topics_file.close()
	digest_file.close()    
	# Stat the digest file for length, and call SendDigest if it's too big
	size = os.stat(os.path.join(self._full_path, "next-digest"))[6]
	if (size/1024.) >= self.digest_size_threshhold:
	    self.SendDigest()

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

	def LikesMime(x, s=self, v=mm_cfg.EnableMime):
	    return s.GetUserOption(x, v)

	def HatesMime(x, s=self, v=mm_cfg.EnableMime):
	    return not s.GetUserOption(x, v)

	recipients = filter(DeliveryEnabled, self.digest_members)
	mime_recipients = filter(LikesMime, recipients)
	text_recipients = filter(HatesMime, recipients)
	digest_log = open('/tmp/digest.log', 'a+')
	digest_log.write('%s digest %d log--\n' % (self.real_name, self.next_digest_number))
	digest_log.write('%d total digesters.  %d w/ Delivery disabled. Of the rest, %d Like MIME.  %d Do not.\n' % (len(self.digest_members), len(self.digest_members) - len(recipients), len(mime_recipients), len(text_recipients)))

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
	digest_file.truncate(0)
	digest_file.close()

	# Create the header and footer... this is a mess!
	topics_file = open(os.path.join(self._full_path, 'next-digest-topics'), 
			   'r+')
	topics_text = topics_file.read()
	topics_file.truncate(0)
	topics_file.close()

	digest_header = '''--%s

From: %s
Subject: Contents of %s digest, Volume %d #%d
Date: %s

Topics for this digest:
%s
''' % (self._mime_separator, msg.GetSender(), self.real_name, self.volume, 
            self.next_digest_number, time.ctime(time.time()), topics_text)

        if self.digest_header:
	    digest_header = digest_header + self.digest_header
	if self.digest_footer:
	    digest_footer = '''--%s

From: %s
Subject: Reminder
Date: %s

%s
--%s--''' % (self._mime_separator, msg.GetSender(), time.ctime(time.time()), 
             self.digest_footer, self._mime_separator)
        else:
	    digest_footer = '''
--%s--''' % self._mime_separator


	def DeliveryEnabled(x, s=self, v=mm_cfg.DisableDelivery):
	    return not s.GetUserOption(x, v)

	def LikesMime(x, s=self, v=mm_cfg.EnableMime):
	    return s.GetUserOption(x, v)

	def HatesMime(x, s=self, v=mm_cfg.EnableMime):
	    return not s.GetUserOption(x, v)

	recipients = filter(DeliveryEnabled, self.digest_members)
	mime_recipients = filter(LikesMime, recipients)
	text_recipients = filter(HatesMime, recipients)
	digest_log = open('/tmp/digest.log', 'a+')
	digest_log.write('%s digest %d log--\n' % (self.real_name, self.next_digest_number))
	digest_log.write('%d total digesters.  %d w/ Delivery disabled. Of the rest, %d Like MIME.  %d Do not.\n' % (len(self.digest_members), len(self.digest_members) - len(recipients), len(mime_recipients), len(text_recipients)))
	self.DeliverToList(msg, mime_recipients, digest_header, 
	                   digest_footer, remove_to=1, tmpfile_prefix = "mime.")
	msg.SetHeader('content-type', 'text/plain', crush_duplicates=1)
	self.DeliverToList(msg, text_recipients, digest_header,
			   digest_footer, remove_to=1)
	self.next_digest_number = self.next_digest_number + 1
	self.next_post_number = 1
	self.Save()
