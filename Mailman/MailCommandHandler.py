# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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


"""Process mailing list user commands arriving via email."""

# Try to stay close to majordomo commands, but accept common mistakes.
# Not implemented: get / index / which.

import os
import sys
import re
import traceback
import email.Iterators
from cStringIO import StringIO

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import Message
from Mailman import Pending
from Mailman.UserDesc import UserDesc
from Mailman.Logging.Syslog import syslog
import Mailman.i18n



MAXERRORS = 5
MAXCOLUMN = 70

NL = '\n'
SPACE = ' '

# jcrey: I must to do a trick to make pygettext detect this strings.  First we
# define a fake function.  Idea taken from Mads.
def _(s):
    return s



# Command descriptions

HIDE = _('''When turned on, your email address is concealed on the Web page
that lists the members of the mailing list.''')

NOMAIL = _('''When turned on, delivery to your email address is disabled, but
your address is still subscribed.  This is useful if you plan on taking a
short vacation.''')

ACK = _('''When turned on, you get a separate acknowledgement email when you
post messages to the list.''')

NOTMETOO = _('''When turned on, you do *not* get copies of your own posts to
the list.  Otherwise, you do get copies of your own posts (yes, this seems a
little backwards).  This does not affect the contents of digests, so if you
receive postings in digests, you will always get copies of your messages in
the digest.''')

DIGEST = _('''When turned on, you get postings from the list bundled into
digests.  Otherwise, you get each individual message immediately as it is
posted to the list.''')

PLAIN = _("""When turned on, you get `plain' digests, which are actually
formatted using the RFC1154 digest format.  This format can be easier to read
if you have a non-MIME compliant mail reader.  When this option is turned off,
you get digests in MIME format, which are much better if you have a mail
reader that supports MIME.""")

option_desc = {'hide'    : HIDE,
               'nomail'  : NOMAIL,
               'ack'     : ACK,
               'notmetoo': NOTMETOO,
               'digest'  : DIGEST,
               'plain'   : PLAIN,
               }

# jcrey: and then the real one
_ = Mailman.i18n._

option_info = {'hide'    : mm_cfg.ConcealSubscription,
               'nomail'  : mm_cfg.DisableDelivery,
               'ack'     : mm_cfg.AcknowledgePosts,
               'notmetoo': mm_cfg.DontReceiveOwnPosts,
               'digest'  : 0,
               'plain'   : mm_cfg.DisableMime,
               }

# ordered list
options = ('hide', 'nomail', 'ack', 'notmetoo', 'digest', 'plain')

# strip just the outer layer of quotes
quotecre = re.compile(r'["\'`](?P<cmd>.*)["\'`]')



class MailCommandHandler:
    def __init__(self):
        self.__errors = 0
        self.__respbuf = ''
        self.__dispatch = {
            'subscribe'   : self.ProcessSubscribeCmd,
            'join'        : self.ProcessSubscribeCmd,
            'confirm'     : self.ProcessConfirmCmd,
            'unsubscribe' : self.ProcessUnsubscribeCmd,
            'remove'      : self.ProcessUnsubscribeCmd,
            'leave'       : self.ProcessUnsubscribeCmd,
            'who'         : self.ProcessWhoCmd,
            'info'        : self.ProcessInfoCmd,
            'lists'       : self.ProcessListsCmd,
            'help'        : self.ProcessHelpCmd,
            'set'         : self.ProcessSetCmd,
            'options'     : self.ProcessOptionsCmd,
            'password'    : self.ProcessPasswordCmd,
            }
        self.__noresponse = 0

    def AddToResponse(self, text, trunc=MAXCOLUMN, prefix=''):
        # Strip final newline
        if text and text[-1] == '\n':
            text = text[:-1]
        for line in text.split('\n'):
            line = prefix + line
            if trunc and len(line) > trunc:
                line = line[:trunc-3] + '...'
            self.__respbuf += line + '\n'

    def AddError(self, text, prefix='>>>>> ', trunc=MAXCOLUMN):
        self.__errors += 1
        self.AddToResponse(text, trunc=trunc, prefix=prefix)
        
    def ParseMailCommands(self, msg, msgdata):
        self.__noresponse = 0
        # Break any infloops.  If this has come from a Mailman server then
        # it'll have this header.  It's still possible to infloop between two
        # servers because there's no guaranteed way to know it came from a
        # bot.
        if msg['x-beenthere'] or msg['list-id']:
            return
        # Check the autoresponse stuff
        if self.autorespond_requests:
            # BAW: this is a hack and is not safe with respect to errors in
            # the Replybot module.  It should be redesigned to work with the
            # robust delivery scheme.
            from Mailman.Handlers import Replybot
            # BAW: Replybot doesn't currently support multiple languages
            Replybot.process(self, msg, msgdata={'torequest':1})
            if self.autorespond_requests == 1:
                # Yes, auto-respond and discard
                return
        subject = msg.get('subject', '')
        sender = msg.get_sender().lower().split('@')[0]
        #
        # XXX: why 'orphanage'?
        if sender in mm_cfg.LIKELY_BOUNCE_SENDERS:
            # This is for what are probably delivery-failure notices of
            # subscription confirmations that are, of necessity, bounced
            # back to the -request address.
            syslog('bounce', '''\
%s: Mailcmd rejected
Reason: Probable bounced subscribe-confirmation
From: %s
Subject: %s''', self.internal_name(), msg['from'], subject)
            return
        if subject:
            subject = subject.strip()
            # remove quotes so "help" works
            mo = quotecre.search(subject)
            if mo:
                subject = mo.group('cmd')

        lines = email.Iterators.body_line_iterator(msg)

        # Find out if the subject line has a command on it
        subjcmd = []
        if subject:
            cmdfound = 0
            for word in subject.split():
                word = word.lower()
                if cmdfound:
                    subjcmd.append(word)
                elif self.__dispatch.has_key(word):
                    cmdfound = 1
                    subjcmd.append(word)
        if subjcmd:
            lines.insert(0, SPACE.join(subjcmd))
        else:
            self.AddError(_('Subject line ignored:\n  ') + subject)
        processed = {}                      # For avoiding redundancies.
        maxlines = mm_cfg.DEFAULT_MAIL_COMMANDS_MAX_LINES
        for linecount in range(len(lines)):
            if linecount > maxlines:
                self.AddError(_(
"Maximum command lines (%(maxlines)d) encountered, ignoring the rest..."))
                for line in lines[linecount:]:
                    self.AddToResponse("> " + line, trunc=0)
                break
            line = lines[linecount].strip()
            if not line:
                continue
            args = line.split()
            cmd = args[0].lower()
            # remove quotes so "help" or `help' works
            mo = quotecre.search(cmd)
            if mo:
                cmd = mo.group('cmd')
            args = args[1:]
            if cmd in ['end', '--']:
                self.AddToResponse('\n***** ' + _('End: ') + line + '\n' +
                                   _('The rest of the message is ignored:'))
                for line in lines[linecount+1:]:
                    self.AddToResponse(line, trunc=0, prefix='> ')
                break
            if not self.__dispatch.has_key(cmd):
                self.AddError(line, prefix=_('Command? '))
                if self.__errors >= MAXERRORS:
                    self.AddError(_(
'\nToo many errors encountered; the rest of the message is ignored:'))
                    for line in lines[linecount+1:]:
                        self.AddToResponse(line, trunc=0, prefix='> ')
                    break
            else:
                # We do not repeat identical commands.  (Eg, it's common
                # with other mlm's for people to put a command in the
                # subject and the body, uncertain which one has effect...)
                isdup = 0
                if not processed.has_key(cmd):
                    processed[cmd] = []
                else:
                    for did in processed[cmd]:
                        if args == did:
                            isdup = 1
                            break
                if not isdup:
                    processed[cmd].append(args)
                    self.AddToResponse('\n***** ' + line)
                    try:
                        # note that all expected exceptions must be handled by 
                        # the dispatch function.  We'll globally collect any
                        # unexpected (e.g. uncaught) exceptions here.  Such an 
                        # exception stops parsing of email commands
                        # immediately
                        self.__dispatch[cmd](args, line, msg)
                    except:
                        admin = self.GetAdminEmail()
                        sfp = StringIO()
                        traceback.print_exc(file=sfp)
                        tbmsg = sfp.getvalue()
                        errmsg = Utils.wrap(_('''\
An unexpected Mailman error has occurred.

Please forward your request to the human list administrator in charge of this
list at <%(admin)s>.  The traceback is attached below and will be forwarded to
the list administrator automatically.'''))
                        self.AddError(errmsg, trunc=0)
                        self.AddToResponse('\n' + tbmsg, trunc=0)
                        # log it to the error file
                        syslog('error',
                               'Unexpected Mailman error:\n%s', tbmsg)
                        # and send the traceback to the user
                        responsemsg = Message.UserNotification(
                            admin, admin, _('Unexpected Mailman error'),
                            _('''\
An unexpected Mailman error has occurred in
MailCommandHandler.ParseMailCommands().  Here is the traceback:

''') + tbmsg)
                        responsemsg['X-No-Archive'] = 'yes'
                        lang = msgdata.get('lang',
                                           self.getMemberLanguage(admin))
                        responsemsg.add_header('Content-Type', 'text/plain',
                                               charset=Utils.GetCharSet(lang))
                        responsemsg.send(self)
                        break
        # send the response
        if not self.__noresponse:
            adminaddr = self.GetAdminEmail()
            requestaddr = self.GetRequestEmail()
            if self.__errors > 0:
                header = Utils.wrap(_('''This is an automated response.

There were problems with the email commands you sent to Mailman via the
administrative address %(requestaddr)s.

To obtain instructions on valid Mailman email commands, send email to
%(requestaddr)s with the word "help" in the subject line or in the body of the
message.

If you want to reach the human being that manages this mailing list, please
send your message to %(adminaddr)s.

The following is a detailed description of the problems.

'''))
                self.__respbuf = header + self.__respbuf
            # send the response
            realname = self.real_name
            subject = _('Mailman results for %(realname)s')
            sender = msg.get_sender()
            lang = msgdata.get('lang', self.getMemberLanguage(sender))
            responsemsg = Message.UserNotification(msg.get_sender(),
                                                   self.GetRequestEmail(),
                                                   subject,
                                                   self.__respbuf)
            responsemsg.add_header('Content-Type', 'text/plain',
                                   charset=Utils.GetCharSet(lang))
            responsemsg.send(self)
            self.__respbuf = ''
            self.__errors = 0

    def ProcessPasswordCmd(self, args, cmd, mail):
        if len(args) <> 0 and len(args) <> 2:
            self.AddError(_("Usage: password [<oldpw> <newpw>]"))
            return
        sender = mail.get_sender()
        if not args:
            # Mail user's password to user
            try:
                password = self.getMemberPassword(sender)
            except Errors.NotAMember:
                password = None
            if self.isMember(sender) and password:
                user = self.getMemberCPAddress(sender)
                self.AddToResponse(_(
               'You are subscribed as %(user)s, with password: %(password)s'),
                                   trunc=0)
            else:
                self.AddError(_('Found no password for %(sender)s'), trunc=0)
            return
        # Try to change password
        try:
            oldpw = self.getMemberPassword(sender)
            if oldpw <> args[0]:
                self.AddError(_('You gave the wrong password.'))
            else:
                self.setMemberPassword(sender, args[1])
                self.AddToResponse(_('Succeeded.'))
        except Errors.NotAMemberError:
            self.AddError(_("%(sender)s is not a member of this list."),
                          trunc=0)

    def ProcessOptionsCmd(self, args, cmd, mail):
        sender = mail.get_sender()
        if not self.isMember(sender):
            self.AddError(_("%(sender)s is not a member of this list."),
                          trunc=0)
            return
        for option in options:
            if self.getMemberOption(sender, option_info[option]):
                value = 'on'
            else:
                value = 'off'
            self.AddToResponse('%8s: %s' % (option, value))
        self.AddToResponse(_("""\
To change an option, do: set <option> <on|off> <password>

Option explanations:
--------------------
"""))
        for option in options:
            self.AddToResponse(option + ':')
            self.AddToResponse(Utils.wrap(_(option_desc[option])) + '\n',
                               trunc=0, prefix="  ")
            
    def __setcmd_usage(self):
        options = option_desc.keys()
        options.sort()
        text = []
        for option in options:
            text.append('%12s:  %s' % (option, _(option_desc[option])))
        self.AddError(_('''\
Usage: set <option> <on|off> <password>
Valid options are:
''') + NL.join(text), trunc=0)

    def ProcessSetCmd(self, args, cmd, msg):
        sender = msg.get_sender()
        if len(args) <> 3:
            self.__setcmd_usage()
            return
        if args[1] == 'on':
            value = 1
        elif args[1] == 'off':
            value = 0
        else:
            self.__setcmd_usage()
            return
        # Check the command
        option = args[0]
        # Backwards compatibility
        if option == 'norcv':
            option = 'notmetoo'
        if not option_info.has_key(option):
            self.__setcmd_usage()
            return
        # Confirm the password
        try:
            password = self.getMemberPassword(sender)
        except Errors.NotAMemberError:
            self.AddError(_("%(sender)s is not a member of this list."),
                          trunc=0)
            return
        if password <> args[2]:
            self.AddError(_('You gave the wrong password.'))
            return

        # Set the option
        try:
            self.setMemberOption(sender, option_info[option], value)
            self.AddToResponse(_('Succeeded.'))
        except Errors.AlreadyReceivingDigests:
            self.AddError(_('You are already receiving digests.'))
        except Errors.AlreadyReceivingRegularDeliveries:
            self.AddError(_('You already have digests off.'))
        except Errors.MustDigestError:
            self.AddError(_('List only accepts digest members.'))
        except Errors.CantDigestError:
            self.AddError(_("List doesn't accept digest members."))
        except Errors.MMNeedApproval:
            self.AddApprovalMsg(cmd)
            
    def ProcessListsCmd(self, args, cmd, mail):
        if len(args) != 0:
            self.AddError(_("Usage: lists"))
            return
        lists = Utils.list_names()
        lists.sort()
        hostname = self.host_name
        self.AddToResponse(_(
            "\nPublic mailing lists run by mailman@%(hostname)s"),
                           trunc=0)
        for listname in lists:
            if listname == self._internal_name:
                listob = self
            else:
                try:
                    from Mailman import MailList
                    listob = MailList.MailList(listname, lock=0)
                except Errors.MMListError, e:
                    # TBD: better error reporting
                    continue
            # We can mention this list if you already know about it.
            if not listob.advertised and listob <> self: 
                continue
            self.AddToResponse(listob.real_name + ':')
            self.AddToResponse(_('\trequests to: ') + listob.GetRequestEmail(),
                               trunc=0)
            if listob.description:
                self.AddToResponse(_('\tdescription: ') + listob.description,
                                   trunc=0)
        
    def ProcessInfoCmd(self, args, cmd, mail):
        if len(args) != 0:
            self.AddError(_("""
Usage: info
To get info for a particular list, send your request to
the `-request' address for that list, or use the `lists' command
to get info for all the lists."""))
            return

        if self.private_roster and not self.isMember(mail.get_sender()):
            self.AddError(_("Private list: only members may see info."))
            return

        msg = Utils.wrap(_('''
For more complete info about the %(listname)s mailing list, including
background and instructions for subscribing to and using it, visit:

    %(url)s

'''))
        self.AddToResponse(msg, trunc=0)

        if not self.info:
            self.AddToResponse(_("No other details are available."))
        else:
            self.AddToResponse(Utils.wrap(self.info), trunc=0)
        
    def ProcessWhoCmd(self, args, cmd, mail):
        if len(args) != 0:
            self.AddError(_("""\
Usage: who
To get subscribership for a particular list, send your request
to the `-request' address for that list."""))
            return
        if self.private_roster == 2:
            self.AddError(_("Private list: No one may see subscription list."))
            return
        if self.private_roster and not self.isMember(mail.get_sender()):
            self.AddError(_(
                "Private list: only members may see list of subscribers."))
            return
        digestmembers = self.getDigestMemberKeys()
        members = self.getRegularMemberKeys()
        if not digestmembers and not members:
            self.AddToResponse(_("NO MEMBERS."))
            return
        
        def AddTab(str):
            return '\t' + str
        def NotHidden(x, s=self, v=mm_cfg.ConcealSubscription):
            return not s.getMemberOption(x, v)

        if len(digestmembers):
            digestmembers.sort()
            self.AddToResponse(_("Digest Members:\n") +
                               NL.join(map(AddTab, filter(NotHidden,
                                                          digestmembers))),
                               trunc=0)
        if len(members):
            members.sort()
            self.AddToResponse(_("Non-Digest Members:\n") +
                               NL.join(map(AddTab, filter(NotHidden,
                                                          members))),
                               trunc=0)

    def ProcessUnsubscribeCmd(self, args, cmd, msg):
        password = None
        if not args:
            # No password and no address.  We can sniff the address, and we
            # will do a confirmation notice.
            addr = msg.get_sender()
        elif len(args) == 1:
            # We only got one argument, so we're not sure if that's the user's
            # address or password.  If the argument is a subscribed user, then
            # assume its the address and send a confirmation notice.
            # Otherwise, assume it's a password.  This could seem weird if
            # they're using their address as their password, but even still,
            # it's not too bad.
            if self.isMember(args[0]):
                addr = args[0]
            else:
                addr = msg.get_sender()
                password = args[0]
        elif len(args) == 2:
            password = args[0]
            addr = args[1]
        else:
            self.AddError(Utils.wrap(
                _("""\
Usage: unsubscribe [password] [email-address]
To unsubscribe from a particular list, send your request to
the `-request' address for that list."""),
                honor_leading_ws = 0),
                          trunc = 0)
            return
        try:
            if password is None:
                # If no password was given, we need to do a mailback
                # confirmation instead of unsubscribing them here.
                cpaddr = self.getMemberCPAddress(addr)
                self.ConfirmUnsubscription(cpaddr)
                self.AddToResponse(
                    _('A removal confirmation message has been sent.'))
            else:
                oldpw = self.getMemberPassword(addr)
                if oldpw <> password:
                    self.AddError(_('You gave the wrong password.'))
                else:
                    self.ApprovedDeleteMember(addr, 'mailcmd')
                    self.AddToResponse(_("Succeeded."))
        # FIXME: we really need to make these exceptions sane!
        except (Errors.MMNoSuchUserError, Errors.MMNotAMemberError,
                Errors.NotAMemberError):
            # For compatibility with similar strings above :(
            sender = addr
            self.AddError(_("%(sender)s is not a member of this list."),
                          trunc=0)

    def ProcessSubscribeCmd(self, args, cmd, mail):
        """Parse subscription request and send confirmation request."""
        digest = self.digest_is_default
        password = ""
        address = ""
        done_digest = 0
        if not len(args):
            password = Utils.MakeRandomPassword()
        elif len(args) > 3:
            self.AddError(_("""\
Usage: subscribe [password] [digest|nodigest] [address=<email-address>]"""),
                          trunc=0)
            return
        else:
            for arg in args:
                if arg.lower() == 'digest' and not done_digest:
                    digest = 1
                    done_digest = 1
                elif arg.lower() == 'nodigest' and not done_digest:
                    digest = 0
                    done_digest = 1
                elif arg.lower()[:8] == 'address=' and not address:
                    address = Utils.LCDomain(arg[8:])
                elif not password:
                    password = arg
                else:
                    self.AddError(_("""\
Usage: subscribe [password] [digest|nodigest] [address=<email-address>]"""))
                    return
        if not password:
            password = Utils.MakeRandomPassword()
        if not address:
            subscribe_address = Utils.LCDomain(mail.get_sender())
        else:
            subscribe_address = address
        remote = mail.get_sender()
        try:
            # FIXME: extract fullname
            userdesc = UserDesc(address=subscribe_address,
                                password=password,
                                digest=digest)
            self.AddMember(userdesc, remote)
            self.Save()
        except Errors.MMSubscribeNeedsConfirmation:
            #
            # the confirmation message that's been sent takes place 
            # of the results of the mail command message
            #
            self.__noresponse = 1
        except Errors.MMNeedApproval:
            adminemail = self.GetAdminEmail()
            self.AddToResponse(_("""\
Your subscription request has been forwarded to the  list administrator
at %(adminemail)s for review."""), trunc=0)
        except Errors.MMBadEmailError:
            self.AddError(_("""\
Mailman won't accept the given email address as a valid address.
(E.g. it must have an @ in it.)"""))
        except Errors.MMListNotReadyError:
            self.AddError(_("\
The list is not fully functional, and can not accept subscription requests."))
        except Errors.MMHostileAddress:
            self.AddError(_("""\
Your subscription is not allowed because
the email address you gave is insecure."""))
        except Errors.MMAlreadyAMember:
            self.AddError(_("You are already subscribed!"))
        except Errors.MMCantDigestError:
            self.AddError(
                _("No one can subscribe to the digest of this list!"))
        except Errors.MMMustDigestError:
            self.AddError(_("This list only supports digest subscriptions!"))
        else:
            #
            # if the list sends a welcome message, we don't need a response
            # from the mailcommand handler.
            #
            if self.send_welcome_msg:
                self.__noresponse = 1
            else:
                self.AddToResponse(_("Succeeded"))

    def ProcessConfirmCmd(self, args, cmd, mail):
        """Validate confirmation and carry out the subscription."""
        if len(args) <> 1:
            self.AddError(_("Usage: confirm <confirmation string>\n"))
            return
        try:
            results = self.ProcessConfirmation(args[0])
            op = results[0]
        except Errors.MMBadConfirmation, e:
            # Express in approximate days
            days = int(mm_cfg.PENDING_REQUEST_LIFE / mm_cfg.days(1) + 0.5)
            self.AddError(Utils.wrap(
                _('''\
Invalid confirmation string.  Note that confirmation strings expire
approximately %(days)s days after the initial subscription request.  If your
confirmation has expired, please try to re-submit your subscription.'''),
                honor_leading_ws=0),
                          trunc=0)
        except Errors.MMNeedApproval, admin_addr:
            self.AddToResponse(Utils.wrap(
                _('''\
Your request has been forwarded to the list moderator for approval.'''),
                honor_leading_ws=0),
                               trunc=0)
        except Errors.MMAlreadyAMember:
            # Some other subscription request for this address has
            # already succeeded.
            self.AddError(_('You are already subscribed.'))
        except Errors.MMNoSuchUserError:
            # They've already been unsubscribed
            self.AddError(Utils.wrap(
                _('''You are not a member.  Have you already unsubscribed?'''),
                honor_leading_ws=0),
                          trunc=0)
        else:
            # Send the response unless this was a subscription confirmation,
            # and the list sends a welcome message.
            if op == Pending.SUBSCRIPTION and self.send_welcome_msg:
                self.__noresponse = 1
            else:
                self.AddToResponse(_("Succeeded"))

    def AddApprovalMsg(self, cmd):
        text = Utils.maketext(
            'approve.txt',
            {'requestaddr': self.GetRequestEmail(),
             'cmd'        : cmd,
             'adminaddr'  : self.GetAdminEmail(),
             }, mlist=self)
        self.AddError(text, trunc=0)

    def ProcessHelpCmd(self, args, cmd, mail):
        text = Utils.maketext(
            'help.txt',
            {'listname'    : self.real_name,
             'version'     : mm_cfg.VERSION,
             'listinfo_url': self.GetScriptURL('listinfo', absolute=1),
             'requestaddr' : self.GetRequestEmail(),
             'adminaddr'   : self.GetAdminEmail(),
             }, mlist=self)
        self.AddToResponse(text, trunc=0)

