import string, os, sys, tempfile
import mm_cfg, mm_message, mm_err, mm_utils

# Text for various messages:

POSTACKTEXT = '''
Your message entitled:

	%s

was successfully received by the %s maillist.

(List info page: %s )
'''

CHANGETEXT = '''[PSA SIG maillist member: Your mailing list is being migrated to a new
maillist mechanism which offers more control both to the list members and
to the administrator (and which, surprise surprise, happens to be written
in python).  See more details below.  We will be switching over immediately
after the subscriptions are transferred.  Actual communication on the list
should work pretty much the same (unless, eg, you elect to receive it in
digest mode...)

Ken Manheimer, klm@python.org.]

'''

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
reminder telling you what all your %s maillist passwords are,
and how to unsubscribe or change your options.

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
    def SendTextToUser(self, subject, text, recipient, sender=None):
	if not sender:
	    sender = self.GetAdminEmail()
        mm_utils.SendTextToUser(subject, text, recipient, sender)

    def DeliverToUser(self, msg, recipient):
        # This method assumes the sender is the one given by the message.
        mm_utils.DeliverToUser(msg, recipient,
                               errorsto=Self.GetAdminEmail())

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
        else:
            sp = self.subject_prefix
            if (len(subject) > len(sp)
                and subject[0:len(sp)] == sp):
                # Trim off subject prefix
                subject = subject[len(sp) + 1:]
	body = POSTACKTEXT % (subject, self.real_name,
                              self.GetScriptURL('listinfo'))
	self.SendTextToUser('%s post acknowlegement' % self.real_name,
                            body, sender)

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

##        body = (CHANGETEXT +
##                SUBSCRIBEACKTEXT % (self.real_name, self.host_name,
        body = (SUBSCRIBEACKTEXT % (self.real_name, self.host_name,
				   self.GetScriptURL('listinfo'),
				   self.real_name, self.host_name,
				   password,
                                   self.host_name,
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
