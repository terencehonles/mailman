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


"""Process maillist user commands arriving via email."""

# Try to stay close to majordomo commands, but accept common mistakes.
# Not implemented: get / index / which.

import os
import sys
import string
import re
import Message
import Errors
import mm_cfg
import Utils
import traceback


option_descs = { 'digest' :
		     'receive mail from the list bundled together instead of '
		     'one post at a time',
		 'nomail' :
		     'Stop delivering mail.  Useful if you plan on taking a '
		     'short vacation.',
		 'norcv'  :
		     'Turn this on to NOT receive posts you send to the list. '
		     'does not work if digest is set',
		 'ack'    :
		     'Turn this on to receive acknowlegement mail when you '
		     'send mail to the list',
		 'plain'  :
		    'Get plain, not MIME-compliant, '
		    'digests (only if digest is set)',
		 'hide'   :
		    'Conceals your email from the list of subscribers'
	       }
option_info = { 'digest' : 0,
		'nomail' : mm_cfg.DisableDelivery,
		'norcv'  : mm_cfg.DontReceiveOwnPosts,
		'ack'    : mm_cfg.AcknowlegePosts,
		'plain'  : mm_cfg.DisableMime,
		'hide'   : mm_cfg.ConcealSubscription
		}

class MailCommandHandler:
    def __init__(self):
	self._response_buffer = ''
	self._cmd_dispatch = {
	    'subscribe' : self.ProcessSubscribeCmd,
            'confirm': self.ProcessConfirmCmd,
	    'unsubscribe' : self.ProcessUnsubscribeCmd,
	    'who' : self.ProcessWhoCmd,
	    'info' : self.ProcessInfoCmd,
	    'lists' : self.ProcessListsCmd,
	    'help' : self.ProcessHelpCmd,
	    'set' : self.ProcessSetCmd,
	    'options' : self.ProcessOptionsCmd,
	    'password' : self.ProcessPasswordCmd,
	    }
        self.__NoMailCmdResponse = 0

    def AddToResponse(self, text):
	self._response_buffer = self._response_buffer + text + "\n"

    def AddError(self, text):
	self._response_buffer = self._response_buffer + "**** " + text + "\n"
	
    def ParseMailCommands(self):
	mail = Message.IncomingMessage()
	subject = mail.getheader("subject")
        sender = string.lower(mail.GetSender())
        #
        # shouldn't this be checking the username only part?
        # why 'orphanage'?
        #
        if sender in ['daemon', 'nobody', 'mailer-daemon', 'postmaster',
                      'orphanage', 'postoffice']:
            # This is for what are probably delivery-failure notices of
            # subscription confirmations that are, of necessity, bounced
            # back to the -request address.
            self.LogMsg("bounce",
                        ("%s: Mailcmd rejected"
                         "\n\tReason: Probable bounced subscribe-confirmation"
                         "\n\tFrom: %s"
                         "\n\tSubject: %s"
                         ),
                        self._internal_name,
                        mail.getheader('from'),
                        subject)
            return
	if subject:
	    subject = string.strip(subject)
	if (subject and self._cmd_dispatch.has_key(string.split(subject)[0])):
	    lines = [subject] + string.split(mail.body, '\n')
        else:
	    lines = string.split(mail.body, '\n')
	    if subject:
		#
		# check to see if confirmation request -- special handling
		#
		conf_pat = (r"%s -- confirmation of subscription"
                            r" -- request (\d\d\d\d\d\d)"
                            % re.escape(self.real_name))
		match = re.search(conf_pat, subject)
		if not match:
		    match = re.search(conf_pat, mail.body)
		if match:
		    lines = ["confirm %s" % (match.group(1))]
		else:
		    self.AddError("Subject line ignored: %s" % subject)
        processed = {}                      # For avoiding redundancies.
        maxlines = mm_cfg.DEFAULT_MAIL_COMMANDS_MAX_LINES
	for linecount in range(len(lines)):
	    line = string.strip(lines[linecount])
	    if not line:
		continue
            if linecount > maxlines:
                self.AddToResponse("\n")
                self.AddError("Maximum command lines (%d) encountered,"
                              " ignoring the rest..." % maxlines)
                self.AddToResponse("<<< " + string.join(lines[linecount:],
                                                      "\n<<< "))
                break
	    self.AddToResponse("\n>>>> %s" % line)
	    args = string.split(line)
	    cmd = string.lower(args[0])
	    args = args[1:]
	    if cmd in ['end', '--']:
		self.AddError("End of commands.")
		break
	    if not self._cmd_dispatch.has_key(cmd):
		self.AddError("%s: Command UNKNOWN." % cmd)
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
                    self._cmd_dispatch[cmd](args, line, mail)
        if not self.__NoMailCmdResponse:
            self.SendMailCmdResponse(mail)

    def SendMailCmdResponse(self, mail):
	self.SendTextToUser(subject = 'Mailman results for %s' % 
			              self.real_name,
			    recipient = mail.GetSender(),
			    sender = self.GetRequestEmail(),
			    text = self._response_buffer)
	self._response_buffer = ''

    def ProcessPasswordCmd(self, args, cmd, mail):
	if len(args) <> 2:
	    self.AddError("Usage: password <oldpw> <newpw>")
	    return
        sender = mail.GetSender()
	try:
            self.ConfirmUserPassword(sender, args[0])
	    self.ChangeUserPassword(sender, args[1], args[1])
	    self.AddToResponse('Succeeded.')
	except Errors.MMListNotReady:
	    self.AddError("List is not functional.")
	except Errors.MMNotAMemberError:
	    self.AddError("%s isn't subscribed to this list." % sender)
	except Errors.MMBadPasswordError:
	    self.AddError("You gave the wrong password.")
	except:
            exc = sys.exc_info()
	    self.AddError("An unknown Mailman error occured."
	    self.AddError("Please forward on your request to %s" %
			  self.GetAdminEmail())
            self.LogMsg("error",
                        "MailCommandHandler.ProcessPasswordCmd():\n%s%s, %s",
                        string.join(traceback.format_tb(exc[2])),
                        exc[0], exc[1])

    def ProcessOptionsCmd(self, args, cmd, mail):
	sender = self.FindUser(mail.GetSender())
	if not sender:
	    self.AddError("%s is not a member of the list." % mail.GetSender())
	    return
	options = option_info.keys()
	options.sort()
	value = ''
	for option in options:
	    if self.GetUserOption(sender, option_info[option]):
		value = 'on'
	    else:
		value = 'off'
	    self.AddToResponse("%s: %s" % (option, value))
	self.AddToResponse("")
	self.AddToResponse("To change an option, do: "
                           "set <option> <on|off> <password>")
	self.AddToResponse("")
	self.AddToResponse("Option explanations:")
	self.AddToResponse("--------------------")
	for option in options:
	    self.AddToResponse("%s:" % option)
	    self.AddToResponse(option_descs[option])
	    self.AddToResponse("")
	    
    def ProcessSetCmd(self, args, cmd, mail):
	def ShowSetUsage(s=self, od = option_descs):
	    options = od.keys()
	    options.sort()
	    s.AddError("Usage: set <option> <on|off> <password>")
	    s.AddError("Valid options are:")
	    for option in options:
		s.AddError("%s:  %s" % (option, od[option]))
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
	if option_info.has_key(args[0]):
	    try:
		sender = self.FindUser(mail.GetSender())
		if not sender:
		    self.AddError("You aren't subscribed.")
		    return
		self.ConfirmUserPassword(sender, args[2])
		self.SetUserOption(sender, option_info[args[0]], value)
		self.AddToResponse("Succeeded.")
	    except Errors.MMBadPasswordError:
		self.AddError("You gave the wrong password.")
	    except:
		self.AddError("An unknown Mailman error occured.")
		self.AddError("Please forward on your request to %s" %
			      self.GetAdminEmail())
		self.AddError("%s" % sys.exc_type)
	elif args[0] == 'digest':
	    try:
		self.SetUserDigest(mail.GetSender(), args[2], value)
		self.AddToResponse("Succeeded.")
	    except Errors.MMAlreadyDigested:
		self.AddError("You are already receiving digests.")
	    except Errors.MMAlreadyUndigested:
		self.AddError("You already have digests off.")
	    except Errors.MMBadEmailError:
		self.AddError("Email address '%s' not accepted by Mailman." % 
			      mail.GetSender())
	    except Errors.MMMustDigestError:
		self.AddError("List only accepts digest members.")
	    except Errors.MMCantDigestError:
		self.AddError("List doesn't accept digest members.")
	    except Errors.MMNotAMemberError:
		self.AddError("%s isn't subscribed to this list."
                              % mail.GetSender())
	    except Errors.MMListNotReady:
		self.AddError("List is not functional.")
	    except Errors.MMNoSuchUserError:
		self.AddError("%s is not subscribed to this list."
                              % mail.GetSender())
	    except Errors.MMBadPasswordError:
		self.AddError("You gave the wrong password.")
	    except Errors.MMNeedApproval:
		self.AddApprovalMsg(cmd)
	    except:
		# TODO: Should log the error we got if we got here.
		self.AddError("An unknown Mailman error occured.")
		self.AddError("Please forward on your request to %s" %
			      self.GetAdminEmail())
		self.AddError("%s" % sys.exc_type)
	else:
	    ShowSetUsage()
	    return
	    
    def ProcessListsCmd(self, args, cmd, mail):
	if len(args) != 0:
	    self.AddError("Usage: lists")
	    return
	lists = os.listdir(mm_cfg.LIST_DATA_DIR)
	lists.sort()
	self.AddToResponse("** Public mailing lists run by Mailman@%s:"
			   % self.host_name)
	for list in lists:
	    if list == self._internal_name:
		listob = self
	    else:
		try:
		    import MailList
		    listob = MailList.MailList(list)
		except:
		    continue
	    # We can mention this list if you already know about it.
	    if not listob.advertised and listob <> self: 
		continue
	    self.AddToResponse("%s (requests to %s):\n\t%s" % 
			       (listob.real_name, listob.GetRequestEmail(),
				listob.description))
	
    def ProcessInfoCmd(self, args, cmd, mail):
	if len(args) != 0:
	    self.AddError("Usage: info\n"
                          "To get info for a particular list, "
                          "send your request to\n"
                          "the '-request' address for that list, or "
                          "use the 'lists' command\n"
                          "to get info for all the lists.")
	    return

	if self.private_roster and not self.IsMember(mail.GetSender()):
	    self.AddError("Private list: only members may see info.")
	    return

        self.AddToResponse("\nFor more complete info about %s, including"
                           " background" % self.real_name)
        self.AddToResponse("and instructions for subscribing to and"
                           " using it, visit:\n\n\t%s\n"
                           % self.GetAbsoluteScriptURL('listinfo'))

	if not self.info:
	    self.AddToResponse("No other details about %s are available." %
			       self.real_name)
	else:
            self.AddToResponse("Here is the specific description of %s:\n"
                               % self.real_name)
            # Put a blank line between the paragraphs, as indicated by CRs.
	    self.AddToResponse(string.join(string.split(self.info, "\n"),
					   "\n\n"))
	
    def ProcessWhoCmd(self, args, cmd, mail):
	if len(args) != 0:
	    self.AddError("To get subscribership for a particular list, "
                          "send your request\n"
                          "to the '-request' address for that list.")
	    return
	def AddTab(str):
	    return '\t' + str

	if self.private_roster == 2:
	    self.AddError("Private list: No one may see subscription list.")
	    return
	if self.private_roster and not self.IsMember(mail.GetSender()):
	    self.AddError("Private list: only members may see list "
			  "of subscribers.")
	    return
        digestmembers = self.GetDigestMembers()
        members = self.GetMembers()
	if not len(digestmembers) and not len(members):
	    self.AddToResponse("NO MEMBERS.")
	    return
	
	def NotHidden(x, s=self, v=mm_cfg.ConcealSubscription):
	    return not s.GetUserOption(x, v)


	if len(digestmembers):
	    self.AddToResponse("")
	    self.AddToResponse("Digest Members:")
            digestmembers.sort()
	    self.AddToResponse(string.join(map(AddTab,
                                               filter(NotHidden,
                                                      digestmembers)),
                                           "\n"))
	if len(members):
	    self.AddToResponse("Non-Digest Members:")
            members.sort()
	    self.AddToResponse(string.join(map(AddTab,
                                               filter(NotHidden, members)),
                                           "\n"))

    def ProcessUnsubscribeCmd(self, args, cmd, mail):
	if not len(args):
	    self.AddError("Must supply a password.")
	    return
	if len(args) > 2:
	    self.AddError("To get unsubscribe from a particular list, "
                          "send your request\nto the '-request' address"
                          "for that list.")
	    return

	if len(args) == 2:
	    addr = args[1]
	else:
	    addr = mail.GetSender()
	try:
	    self.ConfirmUserPassword(addr, args[0])
	    self.DeleteMember(addr, "mailcmd")
	    self.AddToResponse("Succeeded.")
	except Errors.MMListNotReady:
	    self.AddError("List is not functional.")
	except Errors.MMNoSuchUserError:
	    self.AddError("%s is not subscribed to this list."
                          % mail.GetSender())
	except Errors.MMBadPasswordError:
	    self.AddError("You gave the wrong password.")
	except:
	    # TODO: Should log the error we got if we got here.
	    self.AddError("An unknown Mailman error occured.")
	    self.AddError("Please forward on your request to %s"
                          % self.GetAdminEmail())
	    self.AddError("%s %s" % (sys.exc_type, sys.exc_value))
	    self.AddError("%s" % sys.exc_traceback)

    def ProcessSubscribeCmd(self, args, cmd, mail):
        """Parse subscription request and send confirmation request."""
	digest = self.digest_is_default
        password = ""
        address = ""
        done_digest = 0
	if not len(args):
	    password = "%s%s" % (Utils.GetRandomSeed(), 
				 Utils.GetRandomSeed())
        elif len(args) > 3:
            self.AddError("Usage: subscribe [password] "
                          "[digest|nodigest] [address=<email-address>]")
            return
        else:
            for arg in args:
                if string.lower(arg) == 'digest' and not done_digest:
                    digest = 1
                    done_digest = 1
                elif string.lower(arg) == 'nodigest' and not done_digest:
                    digest = 0
                    done_digest = 1
                elif string.lower(arg)[:8] == 'address=' and not address:
                    address = Utils.LCDomain(arg[8:])
                elif not password:
                    password = arg
                else:
                    self.AddError("Usage: subscribe [password] "
                                  "[digest|nodigest] "
                                  "[address=<email-address>]")
                    return
        if not password:
            password = "%s%s" % (Utils.GetRandomSeed(), 
				 Utils.GetRandomSeed())
        if not address:
            subscribe_address = Utils.LCDomain(mail.GetSender())
        else:
            subscribe_address = address
        remote = mail.GetSender()
        try:
            self.AddMember(subscribe_address, password, digest, remote)
            self.Save()
        except Errors.MMSubscribeNeedsConfirmation:
            #
            # the confirmation message that's been sent takes place 
            # of the results of the mail command message
            #
            self.__NoMailCmdResponse = 1
        except Errors.MMNeedApproval, admin_email:
            self.AddToResponse("your subscription request has been forwarded the list "
                               "administrator\nat %s for review.\n" % admin_email)
        except Errors.MMBadEmailError:
            self.AddError("Mailman won't accept the given email "
                          "address as a valid address. \n(Does it "
                          "have an @ in it???)")
        except Errors.MMListNotReady:
            self.AddError("The list is not fully functional, and "
                          "can not accept subscription requests.")
        except Errors.MMHostileAddress:
            self.AddError("Your subscription is not allowed because\n"
                          "the email address you gave is insecure.")
        except Errors.MMAlreadyAMember:
            self.AddError("You are already subscribed!")
        except Errors.MMCantDigestError:
            self.AddError("No one can subscribe to the digest of this list!")
        except Errors.MMMustDigestError:
            self.AddError("This list only supports digest subscriptions!")
        else:
            #
            # if the list sends a welcome message, we don't need a response
            # from the mailcommand handler.
            #
            if self.send_welcome_msg:
                self.__NoMailCmdResponse = 1
            else:
                self.AddToResponse("Succeeded")



    def ProcessConfirmCmd(self, args, cmd, mail):
        """Validate confirmation and carry out the subscription."""
        if len(args) != 1:
            self.AddError("Usage: confirm <confirmation number>\n")
            return
        try:
            cookie = string.atoi(args[0])
        except:
            self.AddError("Usage: confirm <confirmation number>\n")
            return
        try:
            self.ProcessConfirmation(cookie)
        except Errors.MMBadConfirmation:
            from math import floor
            # Express in days, rounded to three places:
            expiredays = floor((mm_cfg.PENDING_REQUEST_LIFE / (60 * 60 * 24.0))
                               * 1000) / 1000
            if floor(expiredays) == expiredays:
                expiredays = int(expiredays)
            self.AddError("Invalid confirmation number!\n"
                          "Note that confirmation numbers expire %s days"
                          " after initial request."
                          "\nPlease check date and number and try again,"
                          " from the start if necessary."
                          % expiredays)
        except Errors.MMNeedApproval, admin_addr:
            self.AddToResponse("your request has been forwarded to the list "
                               "administrator for approval")
            
        else:
            #
            # if the list sends a welcome message, we don't need a response
            # from the mailcommand handler.
            #
            if self.send_welcome_msg:
                self.__NoMailCmdResponse = 1
            else:
                self.AddToResponse("Succeeded")


    def AddApprovalMsg(self, cmd):
        text = Utils.maketext(
            'approve.txt',
            {'requestaddr': self.GetRequestEmail(),
             'cmd'        : cmd,
             'adminaddr'  : self.GetAdminEmail(),
             })
        self.AddError(text)

    def ProcessHelpCmd(self, args, cmd, mail):
        text = Utils.maketext(
            'help.txt',
            {'listname'    : self.real_name,
             'version'     : mm_cfg.VERSION,
             'listinfo_url': self.GetAbsoluteScriptURL('listinfo'),
             'requestaddr' : self.GetRequestEmail(),
             'adminaddr'   : self.GetAdminEmail(),
             })
        self.AddToResponse(text)
