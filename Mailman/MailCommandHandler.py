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

from mimelib.MsgReader import MsgReader

from Mailman import Message
from Mailman import Errors
from Mailman import mm_cfg
from Mailman import Utils
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO
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

option_info = {'digest'  : 0,
               'nomail'  : mm_cfg.DisableDelivery,
               'notmetoo': mm_cfg.DontReceiveOwnPosts,
               'ack'     : mm_cfg.AcknowledgePosts,
               'plain'   : mm_cfg.DisableMime,
               'hide'    : mm_cfg.ConcealSubscription
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
            'confirm'     : self.ProcessConfirmCmd,
            'unsubscribe' : self.ProcessUnsubscribeCmd,
            'who'         : self.ProcessWhoCmd,
            'info'        : self.ProcessInfoCmd,
            'lists'       : self.ProcessListsCmd,
            'help'        : self.ProcessHelpCmd,
            'set'         : self.ProcessSetCmd,
            'options'     : self.ProcessOptionsCmd,
            'password'    : self.ProcessPasswordCmd,
            }
        self.__NoMailCmdResponse = 0

    def AddToResponse(self, text, trunc=MAXCOLUMN, prefix=""):
        # Strip final newline
        if text and text[-1] == '\n':
            text = text[:-1]
        for line in text.split('\n'):
            line = prefix + line
            if trunc and len(line) > trunc:
                line = line[:trunc-3] + '...'
            self.__respbuf = self.__respbuf + line + "\n"

    def AddError(self, text, prefix='>>>>> ', trunc=MAXCOLUMN):
        self.__errors += 1
        self.AddToResponse(text, trunc=trunc, prefix=prefix)
        
    def ParseMailCommands(self, msg, msgdata):
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
            syslog("bounce", "%s: Mailcmd rejected"
                   "\n\tReason: Probable bounced subscribe-confirmation"
                   "\n\tFrom: %s"
                   "\n\tSubject: %s" % (self.internal_name(),
                                        msg['from'], subject))
            return
        if subject:
            subject = subject.strip()
            # remove quotes so "help" works
            mo = quotecre.search(subject)
            if mo:
                subject = mo.group('cmd')

        reader = MsgReader(msg)
        # BAW: here's where Python 2.1's xreadlines module would help!
        lines = []
        while 1:
            line = reader.readline()
            if not line:
                break
            lines.append(line)

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
                self.AddError(_("Maximum command lines (%(maxlines)d) "
                                "encountered, ignoring the rest..."))
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
                    self.AddError(_('\nToo many errors encountered; '
                                  'the rest of the message is ignored:'))
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
                               _('Unexpected Mailman error:\n%(tbmsg)s'))
                        # and send the traceback to the user
                        responsemsg = Message.UserNotification(
                            admin, admin, _('Unexpected Mailman error'),
                            _('''\
An unexpected Mailman error has occurred in
MailCommandHandler.ParseMailCommands().  Here is the traceback:

''') + tbmsg)
                        responsemsg['X-No-Archive'] = 'yes'
                        lang = msgdata.get(
                            'lang',
                            self.GetPreferredLanguage(admin))
                        responsemsg.addheader('Content-Type', 'text/plain',
                                              charset=Utils.GetCharSet(lang))
                        responsemsg.send(self)
                        break
        # send the response
        if not self.__NoMailCmdResponse:
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
            lang = msgdata.get('lang', self.GetPreferredLanguage(sender))
            responsemsg = Message.UserNotification(msg.get_sender(),
                                                   self.GetRequestEmail(),
                                                   subject,
                                                   self.__respbuf)
            responsemsg.addheader('Content-Type', 'text/plain',
                                  charset=Utils.GetCharSet(lang))
            responsemsg.send(self)
            self.__respbuf = ''
            self.__errors = 0
            self.__NoMailCmdResponse = 0

    def ProcessPasswordCmd(self, args, cmd, mail):
        if len(args) not in [0,2]:
            self.AddError(_("Usage: password [<oldpw> <newpw>]"))
            return
        sender = mail.get_sender()
        if len(args) == 0:
            # Mail user's password to user
            user = self.FindUser(sender)
            if user and self.passwords.has_key(user):
                password = self.passwords[user]
                self.AddToResponse(_("You are subscribed as %(user)s,\n"
                                   "  with password: %(password)s"),
                                   trunc=0)
            else:
                self.AddError(_("Found no password for %(sender)s"), trunc=0)
            return
        # Try to change password
        try:
            self.ConfirmUserPassword(sender, args[0])
            self.ChangeUserPassword(sender, args[1], args[1])
            self.AddToResponse(_('Succeeded.'))
        except Errors.MMListNotReadyError:
            self.AddError(_("List is not functional."))
        except Errors.MMNotAMemberError:
            self.AddError(_("%(sender)s isn't subscribed to this list."),
                          trunc=0)
        except Errors.MMBadPasswordError:
            self.AddError(_("You gave the wrong password."))
        except Errors.MMBadUserError:
            self.AddError(_("Bad user - %(sender)s."), trunc=0)

    def ProcessOptionsCmd(self, args, cmd, mail):
        sender = self.FindUser(mail.get_sender())
        if not sender:
            origsender = mail.get_sender()
            self.AddError(_("%(origsender)s is not a member of the list."),
                          trunc=0)
            return
        for option in options:
            if self.GetUserOption(sender, option_info[option]):
                value = 'on'
            else:
                value = 'off'
            self.AddToResponse('%8s: %s' % (option, value))
        self.AddToResponse(_("\n"
                           "To change an option, do: "
                           "set <option> <on|off> <password>\n"
                           "\n"
                           "Option explanations:\n"
                           "--------------------"))
        for option in options:
            self.AddToResponse(option + ':')
            self.AddToResponse(Utils.wrap(_(option_descs[option])) + '\n',
                               trunc=0, prefix="  ")
            
    def ProcessSetCmd(self, args, cmd, mail):
        origsender = mail.get_sender()
        def ShowSetUsage(s=self, od = option_descs):
            options = od.keys()
            options.sort()
            desc_text = ""
            for option in options:
                desc_text = (desc_text +
                             "%12s:  %s\n" % (option, _(od[option])))
            s.AddError(_("Usage: set <option> <on|off> <password>\n"
                       "Valid options are:\n") +
                       desc_text)
        if len(args) <> 3:
            ShowSetUsage()
            return
        if args[1] == 'on':
            value = 1
        elif args[1] == 'off':
            value = 0
        else:
            ShowSetUsage()
            return
        try:
            sender = self.FindUser(origsender)
            self.ConfirmUserPassword(sender, args[2])
        except Errors.MMNotAMemberError:
            self.AddError(_("%(origsender)s isn't subscribed to this list."),
                          trunc=0)
            return
        except Errors.MMBadPasswordError:
            self.AddError(_("You gave the wrong password."))
            return
        if args[0] == 'digest':
            try:
                self.SetUserDigest(origsender, value)
                self.AddToResponse(_("Succeeded."))
            except Errors.MMAlreadyDigested:
                self.AddError(_("You are already receiving digests."))
            except Errors.MMAlreadyUndigested:
                self.AddError(_("You already have digests off."))
            except Errors.MMBadEmailError:
                self.AddError(_(
                    "Email address '%(origsender)s' not accepted by Mailman."),
                              trunc=0)
            except Errors.MMMustDigestError:
                self.AddError(_("List only accepts digest members."))
            except Errors.MMCantDigestError:
                self.AddError(_("List doesn't accept digest members."))
            except Errors.MMListNotReadyError:
                self.AddError(_("List is not functional."))
            except Errors.MMNoSuchUserError:
                self.AddError(_(
                    "%(origsender)s is not subscribed to this list."),
                              trunc=0)
            except Errors.MMNeedApproval:
                self.AddApprovalMsg(cmd)
        elif not option_info.has_key(args[0]):
            ShowSetUsage()
            return
        # for backwards compatibility
        if args[0] == 'norcv':
            args[0] = 'notmetoo'
        self.SetUserOption(sender, option_info[args[0]], value)
        self.AddToResponse(_("Succeeded."))
            
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
            self.AddError(_("Usage: info\n"
                          "To get info for a particular list, "
                          "send your request to\n"
                          "the '-request' address for that list, or "
                          "use the 'lists' command\n"
                          "to get info for all the lists."))
            return

        if self.private_roster and not self.IsMember(mail.get_sender()):
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
            self.AddError(_("Usage: who\n"
                          "To get subscribership for a particular list, "
                          "send your request\n"
                          "to the '-request' address for that list."))
            return
        if self.private_roster == 2:
            self.AddError(_("Private list: No one may see subscription list."))
            return
        if self.private_roster and not self.IsMember(mail.get_sender()):
            self.AddError(_("Private list: only members may see list "
                          "of subscribers."))
            return
        digestmembers = self.GetDigestMembers()
        members = self.GetMembers()
        if not len(digestmembers) and not len(members):
            self.AddToResponse(_("NO MEMBERS."))
            return
        
        def AddTab(str):
            return '\t' + str
        def NotHidden(x, s=self, v=mm_cfg.ConcealSubscription):
            return not s.GetUserOption(x, v)

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

    def ProcessUnsubscribeCmd(self, args, cmd, mail):
        if not len(args):
            self.AddError(_("Usage: unsubscribe <password> [<email-address>]"))
            return
        if len(args) > 2:
            self.AddError(_("Usage: unsubscribe <password> [<email-address>]\n"
                          "To unsubscribe from a particular list, "
                          "send your request\n"
                          "to the '-request' address for that list."))
            return
        if len(args) == 2:
            addr = args[1]
        else:
            addr = mail.get_sender()
        try:
            self.ConfirmUserPassword(addr, args[0])
            self.DeleteMember(addr, "mailcmd")
            self.AddToResponse(_("Succeeded."))
        except Errors.MMListNotReadyError:
            self.AddError(_("List is not functional."))
        except (Errors.MMNoSuchUserError, Errors.MMNotAMemberError):
            self.AddError(_("%(addr)s is not subscribed to this list."),
                          trunc=0)
        except Errors.MMBadPasswordError:
            self.AddError(_("You gave the wrong password."))
        except Errors.MMBadUserError:
            self.AddError(_('Your stored password is bogus.'))
            internalname = self.internal_name()
            syslog('subscribe',
                   _('User %(addr)s on list %(internalname)s has no password'))

    def ProcessSubscribeCmd(self, args, cmd, mail):
        """Parse subscription request and send confirmation request."""
        digest = self.digest_is_default
        password = ""
        address = ""
        done_digest = 0
        if not len(args):
            password = Utils.MakeRandomPassword()
        elif len(args) > 3:
            self.AddError(_("Usage: subscribe [password] "
                          "[digest|nodigest] [address=<email-address>]"),
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
                    self.AddError(_("Usage: subscribe [password] "
                                  "[digest|nodigest] "
                                  "[address=<email-address>]"))
                    return
        if not password:
            password = Utils.MakeRandomPassword()
        if not address:
            subscribe_address = Utils.LCDomain(mail.get_sender())
        else:
            subscribe_address = address
        remote = mail.get_sender()
        try:
            self.AddMember(subscribe_address, password, digest, remote)
            self.Save()
        except Errors.MMSubscribeNeedsConfirmation:
            #
            # the confirmation message that's been sent takes place 
            # of the results of the mail command message
            #
            self.__NoMailCmdResponse = 1
        except Errors.MMNeedApproval:
            adminemail = self.GetAdminEmail()
            self.AddToResponse(_(
                "Your subscription request has been forwarded to the"
                " list administrator\n"
                "at %(adminemail)s for review."), trunc=0)
        except Errors.MMBadEmailError:
            self.AddError(_("Mailman won't accept the given email "
                          "address as a valid address.\n"
                          "(Does it have an @ in it???)"))
        except Errors.MMListNotReadyError:
            self.AddError(_("The list is not fully functional, and "
                          "can not accept subscription\n"
                          "requests."))
        except Errors.MMHostileAddress:
            self.AddError(_("Your subscription is not allowed because\n"
                          "the email address you gave is insecure."))
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
                self.__NoMailCmdResponse = 1
            else:
                self.AddToResponse(_("Succeeded"))

    def ProcessConfirmCmd(self, args, cmd, mail):
        """Validate confirmation and carry out the subscription."""
        if len(args) <> 1:
            self.AddError(_("Usage: confirm <confirmation string>\n"))
            return
        try:
            self.ProcessConfirmation(args[0])
        except Errors.MMBadConfirmation:
            # Express in approximate days
            days = int(mm_cfg.PENDING_REQUEST_LIFE / mm_cfg.days(1) + 0.5)
            self.AddError(_('''Invalid confirmation string.  Note that
            confirmation strings expire approximately %(days)s days after the
            initial subscription request.  If your confirmation has expired,
            please try to re-submit your subscription.'''),
                          trunc=0)
        except Errors.MMNeedApproval, admin_addr:
            self.AddToResponse(_('''Your request has been forwarded to the
            list administrator for approval.'''))
        except Errors.MMAlreadyAMember:
            # Some other subscription request for this address has
            # already succeeded.
            self.AddError(_("You are already subscribed."))
        else:
            #
            # if the list sends a welcome message, we don't need a response
            # from the mailcommand handler.
            #
            if self.send_welcome_msg:
                self.__NoMailCmdResponse = 1
            else:
                self.AddToResponse(_("Succeeded"))

    def AddApprovalMsg(self, cmd):
        text = Utils.maketext(
            'approve.txt',
            {'requestaddr': self.GetRequestEmail(),
             'cmd'        : cmd,
             'adminaddr'  : self.GetAdminEmail(),
             }, lang=self.preferred_language)
        self.AddError(text, trunc=0)

    def ProcessHelpCmd(self, args, cmd, mail):
        text = Utils.maketext(
            'help.txt',
            {'listname'    : self.real_name,
             'version'     : mm_cfg.VERSION,
             'listinfo_url': self.GetScriptURL('listinfo', absolute=1),
             'requestaddr' : self.GetRequestEmail(),
             'adminaddr'   : self.GetAdminEmail(),
             }, lang=self.preferred_language)
        self.AddToResponse(text, trunc=0)

