import string, os, sys
import mm_cfg, mm_message, mm_err

# Text for various messages:

POSTACKTEXT = '''
Your message entitled:
	%s

was successfully received by %s.
'''

SUBSCRIBEACKTEXT = '''Welcome to %s! 

If you ever want to unsubscribe or change your options (eg, switch to  
or from digest mode), visit the web page:

      %s  

You must know your password to change your options or unsubscribe.

Your password is "%s" (no quotes around it).

If you forget your password, don't worry, you will receive a monthly 
reminder telling you what your password is, and how to unsubscribe or 
change your options.  

You may also have your password mailed to you automatically off of 
the web page noted above.


To post to this list, send your email to:

      %s

%s

%s
'''

USERPASSWORDTEXT = '''
This is a reminder of how to unsubscribe or change your configuration
for the mailing list "%s".  You need to have your password for
these things.  YOUR PASSWORD IS:

%s

To make changes, use this password on the web site: 
      %s

Questions or comments?  Send mail to Mailman-owner@%s
'''

# We could abstract these two better...
class Deliverer:
    # This method assumes the sender is list-admin if you don't give one.
    def SendTextToUser(self, subject, text, recipient, sender=None):
	if not sender:
	    sender = self.GetAdminEmail()

	msg = mm_message.OutgoingMessage()
	msg.SetSender(sender)
	msg.SetHeader('Subject', subject, 1)
	msg.SetBody(self.QuotePeriods(text))
	self.DeliverToUser(msg, recipient)

    # This method assumes the sender is the one given by the message.
    def DeliverToUser(self, msg, recipient):
	file = os.popen(mm_cfg.SENDMAIL_CMD % (msg.GetSender(), recipient),
			'w')
	try:
	    msg.headers.remove('\n')
	except:
	    pass
	if not msg.getheader('to'):
	    msg.headers.append('To: %s\n' % recipient)
	msg.headers.append('Errors-To: %s\n' % self.GetAdminEmail())
	file.write(string.join(msg.headers, '')+ '\n') 
	file.write(self.QuotePeriods(msg.body))
	file.close()

    def QuotePeriods(self, text):
	return string.join(string.split(text, '\n.\n'), '\n .\n')
    def DeliverToList(self, msg, recipients, header, footer, remove_to=0,
		      tmpfile_prefix = ""):
	if not(len(recipients)):
	    return
	to_list = string.join(recipients)

# If this is a digest, or we ask to remove them,
# Remove old To: headers.  We're going to stick our own in there.
# Also skip: Sender, return-receipt-to, errors-to, return-path, reply-to,
# (precidence, and received).
        if remove_to:
	    # Writing to a file is better than waiting for sendmail to exit
	    tmp_file_name = '/tmp/%smailman.%d.digest' % (tmpfile_prefix,
							  os.getpid())
	    for item in msg.headers:
		if (item[0:3] == 'To:' or 
		    item[0:5] == 'X-To:'):
		    msg.headers.remove(item)
	    msg.headers.append('To: %s\n' % self.GetListEmail())
	else:
	    tmp_file_name = '/tmp/%smailman.%d' % (tmpfile_prefix, os.getpid())
	msg.headers.append('Errors-To: %s\n' % self.GetAdminEmail())
	tmp_file = open(tmp_file_name, 'w+')

	tmp_file.write(string.join(msg.headers,''))
	# If replys don't go to the list, then they should go to the
	# real sender
	if self.reply_goes_to_list:
	    tmp_file.write('Reply-To: %s\n\n' % self.GetListEmail())
	if header:
	    tmp_file.write(header + '\n\n')
	tmp_file.write(self.QuotePeriods(msg.body))
	if footer:
	    tmp_file.write('\n\n' + footer)
	tmp_file.close()
        file = os.popen("%s %s %s %s %s" %
			(os.path.join(mm_cfg.MAILMAN_DIR, "mail/deliver"),
                         tmp_file_name, self.GetAdminEmail(),
			 self.num_spawns, to_list))

	file.close()

    def SendPostAck(self, msg, sender):
	subject = msg.getheader('subject')
	if not subject:
	    subject = '[none]'
	body = POSTACKTEXT % (subject, self.real_name)
	self.SendTextToUser('Post acknowlegement', body, sender)

    def SendSubscribeAck(self, name, password, digest):
	if digest:
	    digest_mode = '(Digest mode)'
	else:
	    digest_mode = ''

	if self.welcome_msg:
	    header = 'Here is the list-specific information:'
	    welcome = self.welcome_msg
	else:
	    header = ''
	    welcome = ''

	body = SUBSCRIBEACKTEXT % (self.real_name,
				   self.GetScriptURL('listinfo'),
				   password,
				   self.GetListEmail(),
				   header,
				   welcome)

        self.SendTextToUser(subject = 'Welcome To "%s"! %s' % (self.real_name, 
							       digest_mode),
			    recipient = name, 
			    text = body)

    def SendUnsubscribeAck(self, name):
	self.SendTextToUser(subject = 'Unsubscribed from "%s"\n' % 
			               self.real_name,
			    recipient = name, 
			    text = self.goodbye_msg)
    def MailUserPassword(self, user):
	self.SendTextToUser(subject = ('%s@%s maillist reminder\n'
				       % (self.real_name, self.host_name)),
			    recipient = user,
			    text = (USERPASSWORDTEXT
				    % (self.real_name,
				       self.passwords[user],
				       self.GetScriptURL('listinfo'),
				       self.host_name)))
