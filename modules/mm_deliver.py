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


"""Mixin class with message delivery routines."""


import string, os, sys, tempfile
import mm_cfg, mm_message, mm_err, mm_utils

# Text for various messages:

POSTACKTEXT = '''
Your message entitled:

	%s

was successfully received by the %s mailing list.

List info page: %s
'''

SUBSCRIBEACKTEXT = """Welcome to the %(real_name)s@%(host_name)s mailing list!
%(welcome)s
To post to this list, send your email to:

  %(emailaddr)s

General information about the mailing list is at:

  %(generalurl)s

If you ever want to unsubscribe or change your options (eg, switch to or
from digest mode, change your password, etc.), visit your subscription
page at:

  %(optionsurl)s

You can also make such adjustments via email by sending a message to:

  %(real_name)s-request@%(host_name)s

with the word `help' in the subject or body, and you will get back a
message with instructions.

You must know your password to change your options (including changing
the password, itself) or to unsubscribe.  It is:

  %(password)s

If you forget your password, don't worry, you will receive a monthly
reminder telling you what all your %(host_name)s mailing list passwords
are, and how to unsubscribe or change your options.  There is also a
button on your options page that will email your current password to
you.

You may also have your password mailed to you automatically off of the
web page noted above.

"""

USERPASSWORDTEXT = '''
This is a reminder of how to unsubscribe or change your configuration
for the mailing list "%s".  You need to have your password for
these things.  YOUR %s PASSWORD IS:

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
                       add_headers=[], raw=0):
        # repr(recipient) necessary for addresses containing "'" quotes!
        if not sender:
            sender = self.GetAdminEmail()
        mm_utils.SendTextToUser(subject, text, recipient, sender,
                                add_headers=add_headers, raw=raw)

    def DeliverToUser(self, msg, recipient):
        # This method assumes the sender is the one given by the message.
        mm_utils.DeliverToUser(msg, recipient,
                               add_headers=['Errors-To: %s\n'
                                            % Self.GetAdminEmail()])

    def QuotePeriods(self, text):
	return string.join(string.split(text, '\n.\n'), '\n .\n')
    def DeliverToList(self, msg, recipients, 
                      header="", footer="", remove_to=0, tmpfile_prefix = ""):
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
            del msg['to']
            del msg['x-to']
	    msg.headers.append('To: %s\n' % self.GetListEmail())
 	else:
            tempfile.template = tmpfile_prefix + 'mailman.'
	if self.reply_goes_to_list:
            del msg['reply-to']
            msg.headers.append('Reply-To: %s\n' % self.GetListEmail())
	msg.headers.append('Sender: %s\n' % self.GetAdminEmail())
	msg.headers.append('Errors-To: %s\n' % self.GetAdminEmail())
	msg.headers.append('X-BeenThere: %s\n' % self.GetListEmail())

        tmp_file_name = tempfile.mktemp()
 	tmp_file = open(tmp_file_name, 'w+')
 	tmp_file.write(string.join(msg.headers,'') + '\n')

	if header:                      # The *body* header:
	    tmp_file.write(header + '\n')
	tmp_file.write(self.QuotePeriods(msg.body))
	if footer:
	    tmp_file.write(footer)
	tmp_file.close()
        cmd = "%s %s %s %s %s %s" % (
            mm_cfg.PYTHON,
            os.path.join(mm_cfg.SCRIPTS_DIR, "deliver"),
            tmp_file_name, self.GetAdminEmail(),
            self.num_spawns, to_list)
        file = os.popen(cmd)
	status = file.close()
        if status:
            sys.stderr.write('Non-zero exit status: %d'
                             '\nCmd: %s' % ((status >> 8), cmd))
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
                              self.GetAbsoluteScriptURL('listinfo'))
	self.SendTextToUser('%s post acknowlegement' % self.real_name,
                            body, sender)

    def CreateSubscribeAck(self, name, password):
	if self.welcome_msg:
	    welcome = self.welcome_msg + '\n'
	else:
	    welcome = ''

        body = SUBSCRIBEACKTEXT % {'real_name' : self.real_name,
                                   'host_name' : self.host_name,
                                   'welcome'   : welcome,
                                   'emailaddr' : self.GetListEmail(),
                                   'generalurl': self.GetAbsoluteScriptURL('listinfo'),
                                   'optionsurl': self.GetAbsoluteOptionsURL(name),
                                   'password'  : password,
                                   }
        return body

    def SendSubscribeAck(self, name, password, digest):
	if digest:
	    digest_mode = '(Digest mode)'
	else:
	    digest_mode = ''

	if self.reminders_to_admins:
	    recipient = "%s-admin@%s" % tuple(string.split(name, '@'))
	else:
	    recipient = name

        self.SendTextToUser(subject = 'Welcome To "%s"! %s' % (self.real_name, 
							       digest_mode),
			    recipient = recipient,
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
	    if self.reminders_to_admins:
		recipient = "%s-admin@%s" % tuple(string.split(user, '@'))
	    else:
		recipient = user
            subj = '%s maillist reminder\n' % subjpref
            text = USERPASSWORDTEXT % (user,
				       self.real_name,
                                       self.passwords[user],
                                       self.GetAbsoluteOptionsURL(user),
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
