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
import mm_cfg
import Errors
import Utils


# Note that the text templates for the various messages have been moved into
# the templates directory.

# We could abstract these two better...
class Deliverer:
    # This method assumes the sender is list-admin if you don't give one.
    def SendTextToUser(self, subject, text, recipient, sender=None,
                       add_headers=[]):
        if not sender:
            sender = self.GetAdminEmail()
        Utils.SendTextToUser(subject, text, recipient, sender,
                                add_headers=add_headers)

    def DeliverToUser(self, msg, recipient):
        # This method assumes the sender is the one given by the message.
        Utils.DeliverToUser(msg, recipient,
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
        # get the text from the template
        body = Utils.maketext(
            'postack.txt',
            {'subject'     : subject,
             'listname'    : self.real_name,
             'listinfo_url': self.GetAbsoluteScriptURL('listinfo'),
             })
	self.SendTextToUser('%s post acknowlegement' % self.real_name,
                            body, sender)

    def CreateSubscribeAck(self, name, password):
	if self.welcome_msg:
	    welcome = self.welcome_msg + '\n'
	else:
	    welcome = ''

        # get the text from the template
        body = Utils.maketext(
            'subscribeack.txt',
            {'real_name'   : self.real_name,
             'host_name'   : self.host_name,
             'welcome'     : welcome,
             'emailaddr'   : self.GetListEmail(),
             'listinfo_url': self.GetAbsoluteScriptURL('listinfo'),
             'optionsurl'  : self.GetAbsoluteOptionsURL(name),
             'password'    : password,
             })
        return body


    def SendSubscribeAck(self, name, password, digest):
        if not self.send_welcome_msg:
	    return
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
        listfullname = '%s@%s' % (self.real_name, self.host_name)
        ok = 1
        if self.passwords.has_key(user):
	    if self.reminders_to_admins:
		recipient = "%s-admin@%s" % tuple(string.split(user, '@'))
	    else:
		recipient = user
            subj = '%s maillist reminder\n' % listfullname
            # get the text from the template
            text = Utils.maketext(
                'userpass.txt',
                {'user'       : user,
                 'listname'   : self.real_name,
                 'password'   : self.passwords[user],
                 'options_url': self.GetAbsoluteOptionsURL(user),
                 'requestaddr': self.GetRequestEmail(),
                 'adminaddr'  : self.GetAdminEmail(),
                 })
        else:
            ok = 0
            recipient = self.GetAdminEmail()
            subj = '%s user %s missing password!\n' % (listfullname, user)
            text = Utils.maketext(
                'nopass.txt',
                {'username'     : `user`,
                 'internal_name': self._internal_name,
                 })

	self.SendTextToUser(subject = subj,
			    recipient = recipient,
                            text = text,
                            add_headers=["Errors-To: %s"
                                         % self.GetAdminEmail(),
                                         "X-No-Archive: yes"])
        if not ok:
             raise Errors.MMBadUserError
