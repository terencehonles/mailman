"""Mixin class with message delivery routines."""

__version__ = "$Revision: 456 $"


import string, os, sys, tempfile
import mm_cfg, mm_message, mm_err, mm_utils

# Text for various messages:

POSTACKTEXT = '''
Your message entitled:

	%s

was successfully received by the %s maillist.

(List info page: %s )
'''

SUBSCRIBEACKTEXT = '''Welcome to the %s@%s mailing list!
%s%s
General information about the maillist is at:

  %s

If you ever want to unsubscribe or change your options (eg, switch to  
or from digest mode, change your password, etc.), visit your subscription
page at:

  %s

You can also make such adjustments via email - send a message to:

  %s-request@%s

with the text "help" in the subject or body, and you will get back a
message with instructions.

You must know your password to change your options (including changing the
password, itself) or to unsubscribe.  It is:

  %s

If you forget your password, don't worry, you will receive a monthly 
reminder telling you what all your %s maillist passwords are,
and how to unsubscribe or change your options.  There is also a button on
your options page that will email your current password to you.

You may also have your password mailed to you automatically off of 
the web page noted above.

To post to this list, send your email to:

   %s
'''

USERPASSWORDTEXT = '''
This is a reminder of how to unsubscribe or change your configuration
for the mailing list "%s".  You need to have your password for
these things.  YOUR PASSWORD IS:

  %s

To make changes to your subscription, use the password on your options web
page:

  %s

You can also make such changes via email - send a message to:

  %s

with the text "help" in the subject or body, and you will be emailed
instructions.

Questions or comments?  Please send them to %s.
'''

# We could abstract these two better...
class Deliverer:
    # This method assumes the sender is list-admin if you don't give one.
    def SendTextToUser(self, subject, text, recipient, sender=None,
                       add_headers=[]):
        # repr(recipient) necessary for addresses containing "'" quotes!
        self.LogMsg("test", "(mmd) plain: %s, repr: %s" % (recipient,
                                                           repr(recipient)))
        if not sender:
            sender = self.GetAdminEmail()
        mm_utils.SendTextToUser(subject, text, recipient, sender,
                                add_headers=add_headers)

    def DeliverToUser(self, msg, recipient):
        # This method assumes the sender is the one given by the message.
        mm_utils.DeliverToUser(msg, recipient,
                               add_headers=['Errors-To: %s\n'
                                            % Self.GetAdminEmail()])

    def QuotePeriods(self, text):
	return string.join(string.split(text, '\n.\n'), '\n .\n')
    def DeliverToList(self, msg, recipients, header, footer, remove_to=0,
		      tmpfile_prefix = ""):
	if not(len(recipients)):
	    return
        # repr(recipient) necessary for addresses containing "'" quotes!
        recipients = map(repr, recipients)
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
	if self.reply_goes_to_list:
            msg.headers.append('Reply-To: %s\n' % self.GetListEmail())
	msg.headers.append('Errors-To: %s\n' % self.GetAdminEmail())

        tmp_file_name = tempfile.mktemp()
 	tmp_file = open(tmp_file_name, 'w+')
 	tmp_file.write(string.join(msg.headers,'') + '\n')

	if header:                      # The *body* header:
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

    def CreateSubscribeAck(self, name, password):
	if self.welcome_msg:
	    header = '\nHere is the list-specific welcome message:\n\n'
	    welcome = self.welcome_msg + '\n'
	else:
	    header = ''
	    welcome = ''

        body = (SUBSCRIBEACKTEXT % (self.real_name, self.host_name,
                                    header, welcome,
                                    self.GetScriptURL('listinfo'),
                                    self.GetOptionsURL(name),
                                    self.real_name, self.host_name,
                                    password,
                                    self.host_name,
                                    self.GetListEmail()))
        return body

    def SendSubscribeAck(self, name, password, digest):
	if digest:
	    digest_mode = '(Digest mode)'
	else:
	    digest_mode = ''

        self.SendTextToUser(subject = 'Welcome To "%s"! %s' % (self.real_name, 
							       digest_mode),
			    recipient = name, 
			    text = self.CreateSubscribeAck(name, password))

    def SendUnsubscribeAck(self, name):
	self.SendTextToUser(subject = 'Unsubscribed from "%s"\n' % 
			               self.real_name,
			    recipient = name, 
			    text = self.goodbye_msg)
    def MailUserPassword(self, user):
        subjpref = '%s@%s' % (self.real_name, self.host_name)
        ok = 1
        if self.passwords.has_key(user):
            recipient = user
            subj = '%s maillist reminder\n' % subjpref
            text = USERPASSWORDTEXT % (self.real_name,
                                       self.passwords[user],
                                       self.GetOptionsURL(user),
                                       self.GetRequestEmail(),
                                       self.GetAdminEmail())
        else:
            ok = 0
            recipient = self.GetAdminEmail()
            subj = '%s user %s missing password!\n' % (subjpref, user)
            text = ("Mailman noticed (in .MailUserPassword()) that:\n\n"
                    "\tUser: %s\n\tList: %s\n\nlacks a password - please"
                    " notify the mailman system manager!"
                    % (`user`, self._internal_name))
	self.SendTextToUser(subject = subj,
			    recipient = recipient,
                            text = text,
                            add_headers=["Errors-To: %s"
                                         % self.GetAdminEmail(),
                                         "X-No-Archive: yes"])
        if not ok:
             raise mm_err.MMBadUserError
