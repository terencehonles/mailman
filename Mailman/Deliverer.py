import string, os, sys, tempfile
import mm_cfg, mm_message, mm_err

# Text for various messages:

POSTACKTEXT = '''
Your message entitled:
	%s

was successfully received by %s.
'''

## CHANGETEXT = '''[PSA SIG maillist member: Your mailing list is being migrated to a new
## maillist mechanism which offers more control both to the list members and
## to the administrator.  Info about getting at the new features is detailed
## below.  We will be switching over to the new list immediately after the
## subscriptions are transferred, and besides this message (and barring
## unforseen bugs^H^H^H^H circumstances), the changeover should be fairly
## transparent.  Bon voyage!  Ken Manheimer, klm@python.org.]

## '''

SUBSCRIBEACKTEXT = '''Welcome to the %s@%s mailing list! 

If you ever want to unsubscribe or change your options (eg, switch to  
or from digest mode, change your password, etc.), visit the web page:

      %s

You can also make these adjustments via email - send a message to:

      %s-request@%s

with the text "help" in the subject or body, and you will get back a
message with instructions.

You must know your password to change your options (including changing the
password, itself) or to unsubscribe.  It is:

      %s

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

You can also make these adjustments via email - send a message to:

      %s-request@%s

with the text "help" in the subject or body, and you will get back a
message with instructions.

Questions or comments?  Send mail to Mailman-owner@%s
'''

# We could abstract these two better...
class Deliverer:
    # This method assumes the sender is list-admin if you don't give one.
    def SendTextToUser(self, subject, text, recipient,
		       sender=None, errors=None):
	if not sender:
	    sender = self.GetAdminEmail()

	msg = mm_message.OutgoingMessage()
	msg.SetSender(sender)
	msg.SetHeader('Subject', subject, 1)
	if errors:
	    msg.SetHeader('Errors-to', errors, 1)
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
        tempfile.tempdir = '/tmp'

## If this is a digest, or we ask to remove them,
## Remove old To: headers.  We're going to stick our own in there.
## Also skip: Sender, return-receipt-to, errors-to, return-path, reply-to,
## (precedence, and received).

        if remove_to:
	    # Writing to a file is better than waiting for sendmail to exit
            tempfile.template = tmpfile_prefix +'mailman-digest.'
	    for item in msg.headers:
		if (item[0:3] == 'To:' or 
		    item[0:5] == 'X-To:'):
		    msg.headers.remove(item)
	    msg.headers.append('To: %s\n' % self.GetListEmail())
 	else:
            tempfile.template = tmpfile_prefix + 'mailman.'
	msg.headers.append('Errors-To: %s\n' % self.GetAdminEmail())

        tmp_file_name = tempfile.mktemp()
 	tmp_file = open(tmp_file_name, 'w+')

 	tmp_file.write(string.join(msg.headers,''))
	# If replys don't go to the list, then they should go to the
	# real sender
	if self.reply_goes_to_list:
	    tmp_file.write('Reply-To: %s\n\n' % self.GetListEmail())
	if header:
	    tmp_file.write(header + '\n')
	tmp_file.write(self.QuotePeriods(msg.body))
	if footer:
	    tmp_file.write(footer)
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

##	body = (CHANGETEXT +
##              SUBSCRIBEACKTEXT % (self.real_name, self.host_name,
        body = (SUBSCRIBEACKTEXT % (self.real_name, self.host_name,
				   self.GetScriptURL('listinfo'),
				   self.real_name, self.host_name,
				   password,
				   self.GetListEmail(),
				   header,
				   welcome))

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
				       self.real_name, self.host_name,
				       self.host_name)))
