"""Process commands arriving via email."""

# Try to stay close to majordomo commands, but accept common mistakes.
# Not implemented: get / index / which.

import string, os, sys
import mm_message, mm_err, mm_cfg, mm_utils

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
	    'unsubscribe' : self.ProcessUnsubscribeCmd,
	    'who' : self.ProcessWhoCmd,
	    'info' : self.ProcessInfoCmd,
	    'lists' : self.ProcessListsCmd,
	    'help' : self.ProcessHelpCmd,
	    'set' : self.ProcessSetCmd,
	    'options' : self.ProcessOptionsCmd,
	    'password' : self.ProcessPasswordCmd,
	    }

    def AddToResponse(self, text):
	self._response_buffer = self._response_buffer + text + "\n"

    def AddError(self, text):
	self._response_buffer = self._response_buffer + "**** " + text + "\n"
	
    def ParseMailCommands(self):
	mail = mm_message.IncomingMessage()
	subject = mail.getheader("subject")
	if subject:
	    subject = string.strip(subject)
	if (subject and self._cmd_dispatch.has_key(string.split(subject)[0])):
	    lines = [subject] + string.split(mail.body, '\n')
        else:
	    lines = string.split(mail.body, '\n')
	    if subject:
		self.AddError("Subject line ignored: %s" % subject)
	for line in lines:
	    line = string.strip(line)
	    if not line:
		continue
	    self.AddToResponse("\n>>>> %s" % line)
	    line = string.strip(line)
	    if not line:
		continue
	    args = string.split(line)
	    cmd = string.lower(args[0])
	    args = args[1:]
	    if cmd == 'end':
		self.AddError("End of commands.")
		break
	    if not self._cmd_dispatch.has_key(cmd):
		self.AddError("%s: Command UNKNOWN." % cmd)
	    else:
		self._cmd_dispatch[cmd](args, line, mail)
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
	try:
	    self.ChangeUserPassword(mail.GetSender(),
				    args[0], args[1], args[1])
	    self.AddToResponse('Succeded.')
	except mm_err.MMListNotReady:
	    self.AddError("List is not functional.")
	except mm_err.MMNotAMemberError:
	    self.AddError("%s isn't subscribed to this list." %
			  mail.GetSender())
	except mm_err.MMBadPasswordError:
	    self.AddError("You gave the wrong password.")
	except:
	    self.AddError("An unknown Mailman error occured.")
	    self.AddError("Please forward on your request to %s" %
			  self.GetAdminEmail())
	    self.AddError("%s" % sys.exc_type)

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
	    except mm_err.MMBadPasswordError:
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
	    except mm_err.MMAlreadyDigested:
		self.AddError("You are already receiving digests.")
	    except mm_err.MMAlreadyUndigested:
		self.AddError("You already have digests off.")
	    except mm_err.MMBadEmailError:
		self.AddError("Email address '%s' not accepted by Mailman." % 
			      mail.GetSender())
	    except mm_err.MMMustDigestError:
		self.AddError("List only accepts digest members.")
	    except mm_err.MMCantDigestError:
		self.AddError("List doesn't accept digest members.")
	    except mm_err.MMNotAMemberError:
		self.AddError("%s isn't subscribed to this list."
                              % mail.GetSender())
	    except mm_err.MMListNotReady:
		self.AddError("List is not functional.")
	    except mm_err.MMNoSuchUserError:
		self.AddError("%s is not subscribed to this list."
                              % mail.GetSender())
	    except mm_err.MMBadPasswordError:
		self.AddError("You gave the wrong password.")
	    except mm_err.MMNeedApproval:
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
		    import maillist
		    listob = maillist.MailList(list)
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

	self.AddToResponse("Here is the info for list %s:" % self.real_name)
	if not self.info:
	    self.AddToResponse("No information on list %s found." %
			       self.real_name)
	else:
	    self.AddToResponse(self.info)
	
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
	if not len(self.digest_members) and not len(self.members):
	    self.AddToResponse("NO MEMBERS.")
	    return
	
	def NotHidden(x, s=self, v=mm_cfg.ConcealSubscription):
	    return not s.GetUserOption(x, v)

	if len(self.digest_members):
	    self.AddToResponse("")
	    self.AddToResponse("Digest Members:")
            digestmembers = self.digest_members[:]
            digestmembers.sort()
	    self.AddToResponse(string.join(map(AddTab,
                                               filter(NotHidden,
                                                      digestmembers)),
                                           "\n"))
	if len(self.members):
	    self.AddToResponse("Non-Digest Members:")
            members = self.members[:]
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
	    self.DeleteMember(addr)
	    self.AddToResponse("Succeded.")
	except mm_err.MMListNotReady:
	    self.AddError("List is not functional.")
	except mm_err.MMNoSuchUserError:
	    self.AddError("%s is not subscribed to this list."
                          % mail.GetSender())
	except mm_err.MMBadPasswordError:
	    self.AddError("You gave the wrong password.")
	except:
	    # TODO: Should log the error we got if we got here.
	    self.AddError("An unknown Mailman error occured.")
	    self.AddError("Please forward on your request to %s"
                          % self.GetAdminEmail())
	    self.AddError("%s %s" % (sys.exc_type, sys.exc_value))
	    self.AddError("%s" % sys.exc_traceback)

    def ProcessSubscribeCmd(self, args, cmd, mail):
	digest = self.digest_is_default
	if not len(args):
	    password = "%s%s" % (mm_utils.GetRandomSeed(), 
				 mm_utils.GetRandomSeed())
	elif len(args) == 1:
	    if string.lower(args[0]) == 'digest':
		digest = 1
		password = "%s%s" % (mm_utils.GetRandomSeed(), 
				 mm_utils.GetRandomSeed())
	    elif string.lower(args[0]) == 'nodigest':
		digest = 0
		password = "%s%s" % (mm_utils.GetRandomSeed(), 
				 mm_utils.GetRandomSeed())
	    else:
		password = args[0]

	elif len(args) == 2:
	    if string.lower(args[1]) == 'nodigest':
		digest = 0
		password = args[0]
	    elif string.lower(args[1]) == 'digest':
		digest = 1
		password = args[0]
	    elif string.lower(args[0]) == 'nodigest':
		digest = 0
		password = args[1]
	    elif string.lower(args[0]) == 'digest':
		digest = 1
		password = args[1]
	    else:
		self.AddError("Usage: subscribe [password] [digest|nodigest]")
		return
	elif len(args) > 2:
		self.AddError("Usage: subscribe [password] [digest|nodigest]")
		return

	try:
	    self.AddMember(mail.GetSender(), password, digest)
	    self.AddToResponse("Succeded.")
	except mm_err.MMBadEmailError:
	    self.AddError("Email address '%s' not accepted by Mailman." % 
			  mail.GetSender())
	except mm_err.MMMustDigestError:
	    self.AddError("List only accepts digest members.")
	except mm_err.MMCantDigestError:
	    self.AddError("List doesn't accept digest members.")
	except mm_err.MMListNotReady:
	    self.AddError("List is not functional.")
	except mm_err.MMNeedApproval:
	    self.AddApprovalMsg(cmd)
        except mm_err.MMHostileAddress:
	    self.AddError("Email address '%s' not accepted by Mailman "
			  "(insecure address)" % mail.GetSender())
	except mm_err.MMAlreadyAMember:
	    self.AddError("%s is already a list member." % mail.GetSender())
	except:
	    # TODO: Should log the error we got if we got here.
	    self.AddError("An unknown Mailman error occured.")
	    self.AddError("Please forward on your request to %s" %
			  self.GetAdminEmail())
	    self.AddError("%s" % sys.exc_type)
		
    def AddApprovalMsg(self, cmd):
        self.AddError('''Your request to %s:

        %s

has been forwarded to the person running the list.

This is probably because you are trying to subscribe to a 'closed' list.

You will receive email notification of the list owner's decision about
your subscription request.

Any questions about the list owner's policy should be directed to:

        %s

''' % (self.GetRequestEmail(), cmd, self.GetAdminEmail()))


    def ProcessHelpCmd(self, args, cmd, mail):
	self.AddToResponse("**** Help for %s maillist:" % self.real_name)
	self.AddToResponse("""
This is email command help for version %s of the "Mailman" list manager.
The following describes commands you can send to get information about and
control your subscription to mailman lists at this site.  A command can
be the subject line or in the body of the message.

(Note that much of the following can also be accomplished via the web, at:

	%s

In particular, you can use the web site to have your password sent to your
delivery address.)

List specific commands (subscribe, who, etc) should be sent to the
*-request address for the particular list, e.g. for the 'mailman' list,
use 'mailman-request@...'.

About the descriptions - words in "<>"s signify REQUIRED items and words in
"[]" denote OPTIONAL items.  Do not include the "<>"s or "[]"s when you use
the commands.

The following commands are valid:

    subscribe [password] [digest-option]
        Subscribe to the mailing list.  Your password must be given to
        unsubscribe or change your options.  When you subscribe to the
        list, you'll be reminded of your password periodically.
        'digest-option' may be either: 'nodigest' or 'digest' (no quotes!)
	To subscribe this way, you must subscribe from the account in 
	which you wish to receive mail.

    unsubscribe <password> [address]
        Unsubscribe from the mailing list.  Your password must match
	the one you gave when you subscribed.  If you are trying to
	unsubscribe from a different address than the one you subscribed
	from, you may specify it in the 'address' field.

    who
        See who is on this mailing list.

    info
        View the introductory information for this list.

    lists
        See what mailing lists are run by this Mailman server.

    help
        This message.

    set <option> <on|off> <password> 
	Turn on or off list options.  Valid options are:

	ack:
	Turn this on to receive acknowlegement mail when you send mail to
	the list 

	digest:
	receive mail from the list bundled together instead of one post at
	a time 

	plain:
	Get plain-text, not MIME-compliant, digests (only if digest is set)

	nomail:
	Stop delivering mail.  Useful if you plan on taking a short vacation.

	norcv:
	Turn this on to NOT receive posts you send to the list. 
	Does not work if digest is set

	hide:
	Conceals your address when people look at who is on this list.


    options
	Show the current values of your list options.

    password <oldpassword> <newpassword> 
        Change your list password.
    
    end
       Stop processing commands (good to do if your mailer automatically
       adds a signature file - it'll save you from a lot of cruft).


Commands should be sent to %s

Questions and concerns for the attention of a person should be sent to
%s
""" % (mm_cfg.VERSION,
       self.GetScriptURL('listinfo'),
       self.GetRequestEmail(),
       self.GetAdminEmail()))
	
