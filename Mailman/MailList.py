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


"""The class representing a Mailman mailing list.

Mixes in many feature classes.
"""

try:
    import mm_cfg
except ImportError:
    raise RuntimeError, ('missing mm_cfg - has mm_cfg_dist been configured '
			 'for the site?')

import sys, os, marshal, string, posixfile, time
import re
import mm_utils, mm_err

from mm_admin import ListAdmin
from mm_deliver import Deliverer
from mm_mailcmd import MailCommandHandler 
from mm_html import HTMLFormatter 
from mm_archive import Archiver
from mm_digest import Digester
from mm_security import SecurityManager
from mm_bouncer import Bouncer

# Note: 
# an _ in front of a member variable for the MailList class indicates
# a variable that does not save when we marshal our state.

# Use mixins here just to avoid having any one chunk be too large.

class MailList(MailCommandHandler, HTMLFormatter, Deliverer, ListAdmin, 
	       Archiver, Digester, SecurityManager, Bouncer):
    def __init__(self, name=None):
	MailCommandHandler.__init__(self)
	self._internal_name = name
	self._ready = 0
	self._log_files = {}		# 'class': log_file_obj
	if name:
	    if name not in mm_utils.list_names():
		raise mm_err.MMUnknownListError, 'list not found: %s' % name
	    self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
	    # Load in the default values so that old data files aren't
	    # hosed by new versions of the program.
	    self.InitVars(name)
	    self.Load()

    def __del__(self):
	for f in self._log_files.values():
	    f.close()

    def GetAdminEmail(self):
        return '%s-admin@%s' % (self._internal_name, self.host_name)

    def GetRequestEmail(self):
	return '%s-request@%s' % (self._internal_name, self.host_name)

    def GetListEmail(self):
	return '%s@%s' % (self._internal_name, self.host_name)

    def GetScriptURL(self, script_name):
        if self.web_page_url:
            prefix = self.web_page_url
        else:
            prefix = mm_cfg.DEFAULT_URL
        return os.path.join(prefix, '%s/%s' % (script_name,
                                               self._internal_name))

    def GetOptionsURL(self, addr, obscured=0):
	options = self.GetScriptURL('options')
        if obscured:
            treated = mm_utils.ObscureEmail(addr, for_text=0)
        else:
            treated = addr
        return os.path.join(options, treated)

    def GetUserOption(self, user, option):
	if option == mm_cfg.Digests:
	    return user in self.digest_members
	if not self.user_options.has_key(user):
	    return 0
	return not not self.user_options[user] & option

    def SetUserOption(self, user, option, value):
	if not self.user_options.has_key(user):
	    self.user_options[user] = 0
	if value:
	    self.user_options[user] = self.user_options[user] | option
	else:
	    self.user_options[user] = self.user_options[user] & ~(option)
	if not self.user_options[user]:
	    del self.user_options[user]
	self.Save()

    def FindUser(self, email):
	matches = mm_utils.FindMatchingAddresses(email,
						 (self.members
						  + self.digest_members))
	if not matches or not len(matches):
	    return None
	return matches[0]

    def InitVars(self, name='', admin='', crypted_password=''):
        """Assign default values - some will be overriden by stored state."""
	# Non-configurable list info 
	self._internal_name = name
	self._lock_file = None
	self._mime_separator = '__--__--' 

	# Must save this state, even though it isn't configurable
	self.volume = 1
	self.members = [] # self.digest_members is initted in mm_digest
	self.data_version = mm_cfg.VERSION
	self.last_post_time = 0
	
	self.post_id = 1.  # A float so it never has a chance to overflow.
	self.user_options = {}

	# This stuff is configurable
	self.filter_prog = mm_cfg.DEFAULT_FILTER_PROG
	self.dont_respond_to_post_requests = 0
	self.num_spawns = mm_cfg.DEFAULT_NUM_SPAWNS
	self.advertised = mm_cfg.DEFAULT_LIST_ADVERTISED
	self.max_num_recipients = mm_cfg.DEFAULT_MAX_NUM_RECIPIENTS
	self.max_message_size = mm_cfg.DEFAULT_MAX_MESSAGE_SIZE
	self.web_page_url = mm_cfg.DEFAULT_URL   
	self.owner = [admin]
	self.reply_goes_to_list = mm_cfg.DEFAULT_REPLY_GOES_TO_LIST
	self.posters = []
	self.forbidden_posters = []
	self.admin_immed_notify = mm_cfg.DEFAULT_ADMIN_IMMED_NOTIFY
	self.moderated = mm_cfg.DEFAULT_MODERATED
	self.require_explicit_destination = \
		mm_cfg.DEFAULT_REQUIRE_EXPLICIT_DESTINATION
        self.acceptable_aliases = mm_cfg.DEFAULT_ACCEPTABLE_ALIASES
	self.reminders_to_admins = mm_cfg.DEFAULT_REMINDERS_TO_ADMINS
	self.bounce_matching_headers = \
		mm_cfg.DEFAULT_BOUNCE_MATCHING_HEADERS
	self.real_name = '%s%s' % (string.upper(self._internal_name[0]), 
				   self._internal_name[1:])
	self.description = ''
	self.info = ''
	self.welcome_msg = ''
	self.goodbye_msg = ''
	self.open_subscribe = mm_cfg.DEFAULT_OPEN_SUBSCRIBE
	self.private_roster = mm_cfg.DEFAULT_PRIVATE_ROSTER
	self.obscure_addresses = mm_cfg.DEFAULT_OBSCURE_ADDRESSES
	self.member_posting_only = mm_cfg.DEFAULT_MEMBER_POSTING_ONLY
	self.web_subscribe_requires_confirmation = \
		mm_cfg.DEFAULT_WEB_SUBSCRIBE_REQUIRES_CONFIRMATION
	self.host_name = mm_cfg.DEFAULT_HOST_NAME

	# Analogs to these are initted in Digester.InitVars
	self.nondigestable = mm_cfg.DEFAULT_NONDIGESTABLE

	Digester.InitVars(self) # has configurable stuff
	SecurityManager.InitVars(self, crypted_password)
	HTMLFormatter.InitVars(self)
	Archiver.InitVars(self) # has configurable stuff
	ListAdmin.InitVars(self)
	Bouncer.InitVars(self)

	# These need to come near the bottom because they're dependent on
	# other settings.
	self.subject_prefix = mm_cfg.DEFAULT_SUBJECT_PREFIX % self.__dict__
	self.msg_header = mm_cfg.DEFAULT_MSG_HEADER
	self.msg_footer = mm_cfg.DEFAULT_MSG_FOOTER

    def GetConfigInfo(self):
	config_info = {}
	config_info['digest'] = Digester.GetConfigInfo(self)
	config_info['archive'] = Archiver.GetConfigInfo(self)

	config_info['general'] = [
            "Fundamental list characteristics, including descriptive"
            " info and basic behaviors.",
	    ('real_name', mm_cfg.String, 50, 0,
	     'The public name of this list (make case-changes only).',

             "The capitalization of this name can be changed to make it"
             " presentable in polite company as a proper noun, or to make an"
             " acronym part all upper case, etc.  However, the name"
             " will be advertised as the email address (e.g., in subscribe"
             " confirmation notices), so it should <em>not</em> be otherwise"
             " altered.  (Email addresses are not case sensitive, but"
             " they are sensitive to almost everything else:-)"),

	    ('owner', mm_cfg.EmailList, (3,30), 0,
	     "The list admin's email address - having multiple"
	     " admins/addresses (on separate lines) is ok."),

	    ('description', mm_cfg.String, 50, 0,
	     'A terse phrase identifying this list.',

             "This description is used when the maillist is listed with"
             " other maillists, or in headers, and so forth.  It should"
             " be as succinct as you can get it, while still identifying"
             " what the list is."),

	    ('info', mm_cfg.Text, (7, 50), 0, 
	     ' An introductory description - a few paragraphs - about the'
	     ' list.  It will be included, as html, at the top of the'
	     ' listinfo page.  Carriage returns will end a paragraph - see'
             ' the details for more info.',

             "The text will be treated as html <em>except</em> that newlines"
             " newlines will be translated to &lt;br&gt; - so you can use"
             " links, preformatted text, etc, but don't put in carriage"
             " returns except where you mean to separate paragraphs.  And"
             " review your changes - bad html (like some unterminated HTML"
             " constructs) can prevent display of the entire listinfo page."),

	    ('subject_prefix', mm_cfg.String, 10, 0,
	     'Prefix for subject line of list postings.',

             "This text will be prepended to subject lines of messages"
             " posted to the list, to distinguish maillist messages in"
             " in mailbox summaries.  Brevity is premium here, it's ok"
             " to shorten long maillist names to something more concise,"
             " as long as it still identifies the maillist."),

	    ('welcome_msg', mm_cfg.Text, (4, 50), 0,
	     'List-specific text prepended to new-subscriber welcome message',

             "This value, if any, will be added to the front of the"
             " new-subscriber welcome message.  The rest of the"
             " welcome message already describes the important addresses"
             " and URLs for the maillist, so you don't need to include"
             " any of that kind of stuff here.  This should just contain"
             " mission-specific kinds of things, like etiquette policies"
             " or team orientation, or that kind of thing."),

	    ('goodbye_msg', mm_cfg.Text, (4, 50), 0,
	     'Text sent to people leaving the list.  If empty, no special'
	     ' text will be added to the unsubscribe message.'),

	    ('reply_goes_to_list', mm_cfg.Radio, ('Poster', 'List'), 0,
	     'Are replies to a post directed to the original poster'
	     ' or to the list?  <tt>Poster</tt> is <em>strongly</em>'
             ' recommended.',

             "There are many reasons not to introduce headers like reply-to"
             " into other peoples messages - one is that some posters depend"
             " on their own reply-to setting to convey their valid email"
             " addr.  See"
             ' <a href="http://www.unicom.com/pw/reply-to-harmful.html">'
             '"Reply-To" Munging Considered Harmful</a> for a general.'
             " discussion of this issue."),

	    ('reminders_to_admins', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Send password reminders to "-admin" address instead of'
	     ' directly to user.',

	     "Set this to yes when this list is intended only to cascade to"
	     " other maillists.  When set, the password reminders will be"
	     " directed to an address derived from the member's address"
	     ' - it will have "-admin" appended to the member\'s account'
	     " name."),

	    ('admin_immed_notify', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Should administrator get immediate notice of new requests, '
	     'as well as daily notices about collected ones?',

             "List admins are sent daily reminders of pending admin approval"
             " requests, like subscriptions to a moderated list or postings"
	     " that are being held for one reason or another.  Setting this"
	     " option causes notices to be sent immediately on the arrival"
	     " of new requests, as well."),

	    ('dont_respond_to_post_requests', mm_cfg.Radio, ('Yes', 'No'), 0,
	     'Send mail to poster when their posting is held for approval?',

             "Approval notices are sent when mail triggers certain of the"
             " limits <em>except</em> routine list moderation and spam"
	     " filters, for which notices are <em>not</em> sent.  This"
	     " option overrides ever sending the notice."),

            # XXX UNSAFE!  Perhaps more selective capability could be
            # offered, with some kind of super-admin option, but for now
            # let's not even expose this.  (Apparently was never
            # implemented, anyway.)
## 	    ('filter_prog', mm_cfg.String, 40, 0,
## 	     'Program for pre-processing text, if any? '
## 	     '(Useful, eg, for signature auto-stripping, etc...)'),

	    ('max_message_size', mm_cfg.Number, 3, 0,
	     'Maximum length in Kb of a message body.  Use 0 for no limit.'),

	    ('num_spawns', mm_cfg.Number, 3, 0,
	     'Number of outgoing connections to open at once '
	     '(expert users only).',

             "This determines the maximum number of batches into which"
             " a mass posting will be divided."),

	    ('host_name', mm_cfg.Host, 50, 0, 'Host name this list prefers.',

             "The host_name is the preferred name for email to mailman-related"
             " addresses on this host, and generally should be the mail"
             " host's exchanger address, if any.  This setting can be useful"
             " for selecting among alternative names of a host that has"
             " multiple addresses."),

 	    ('web_page_url', mm_cfg.String, 50, 0,
 	     'Base URL for Mailman web interface',

             "This is the common root for all mailman URLs concerning this"
             " list.  It can be useful for selecting a particular URL"
             " of a host that has multiple addresses."),
          ]

        config_info['privacy'] = [
            "List access policies, including anti-spam measures,"
            " covering members and outsiders."
            '  (See also the <a href="%s">Archival Options section</a> for'
            ' separate archive-privacy settings.)'
            % os.path.join(self.GetScriptURL('admin'), 'archive'),

	    "Subscribing",

	    ('advertised', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Advertise this list when people ask what lists are on '
	     'this machine?'),

	    ('open_subscribe', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Are subscribes done without admins approval (ie, is this'
             ' an <em>open</em> list)?',

             "Disabling this option makes the list <em>closed</em>, where"
             " members are admitted only at the discretion of the list"
	     " administrator."),

	    ('web_subscribe_requires_confirmation', mm_cfg.Radio,
	     ('None', 'Requestor confirms via email', 'Admin approves'), 0,
	     'What confirmation is required for on-the-web subscribes?',

             "This option determines whether web-initiated subscribes"
             " require further confirmation, either from the subscribed"
             " address or from the list administrator.  Absence of"
             " <em>any</em> confirmation makes web-based subscription a"
             " tempting opportunity for mischievous subscriptions by third"
             " parties."),

            "Membership exposure",

	    ('private_roster', mm_cfg.Radio,
	     ('Anyone', 'List members', 'List admin only'), 0,
	     'Who can view subscription list?',

             "When set, the list of subscribers is protected by"
             " member or admin password authentication."),

	    ('obscure_addresses', mm_cfg.Radio, ('No', 'Yes'), 0,
             "Show member addrs so they're not directly recognizable"
             ' as email addrs?',

             "Setting this option causes member email addresses to be"
             " transformed when they are presented on list web pages (both"
             " in text and as links), so they're not trivially"
             " recognizable as email addresses.  The intention is to"
             " to prevent the addresses from being snarfed up by"
             " automated web scanners for use by spammers."),

            "General posting filters",

	    ('moderated', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Must posts be approved by a moderator?',

             "If the 'posters' option has any entries then it supercedes"
             " this setting."),

	    ('member_posting_only', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Restrict posting privilege to only list members?'),

	    ('posters', mm_cfg.EmailList, (5, 30), 1,
	     'Addresses blessed for posting to this list.  (Adding'
             ' anyone to this list implies moderation of everyone else.)',

             "Adding any entries to this list supercedes the setting of"
             " the list-moderation option."),

            "Spam-specific posting filters",

 	    ('require_explicit_destination', mm_cfg.Radio, ('No', 'Yes'), 0,
 	     'Must posts have list named in destination (to, cc) field'
             ' (or be among the acceptable alias names, specified below)?',

             "Many (in fact, most) spams do not explicitly name their myriad"
             " destinations in the explicit destination addresses - in fact,"
             " often the to field has a totally bogus address for"
             " obfuscation.  The constraint applies only to the stuff in"
             " the address before the '@' sign, but still catches all such"
             "  spams."
             "<p>The cost is that the list will not accept unhindered any"
             " postings relayed from other addresses, unless <ol>"
             " <li>The relaying address has the same name, or"
             " <li>The relaying address name is included on the options that"
             " specifies acceptable aliases for the list. </ol>"),

 	    ('acceptable_aliases', mm_cfg.Text, ('4', '30'), 0,
 	     'Alias names (regexps) which qualify as explicit to or cc'
             ' destination names for this list.',

             "Alternate list names (the stuff before the '@') that are to be"
             " accepted when the explicit-destination constraint (a prior"
             " option) is active.  This enables things like cascading"
             " maillists and relays while the constraint is still"
             " preventing random spams."), 

	    ('max_num_recipients', mm_cfg.Number, 3, 0, 
	     'Ceiling on acceptable number of recipients for a posting.',

             "If a posting has this number, or more, of recipients, it is"
             " held for admin approval.  Use 0 for no ceiling."),

	    ('forbidden_posters', mm_cfg.EmailList, (5, 30), 1,
             'Addresses whose postings are always held for approval.',

	     "Email addresses whose posts should always be held for"
             " approval, no matter what other options you have set."
             " See also the subsequent option which applies to arbitrary"
             " content of arbitrary headers."),

 	    ('bounce_matching_headers', mm_cfg.Text, ('6', '50'), 0,
 	     'Hold posts with header value matching a specified regexp.',

             "Use this option to prohibit posts according to specific header"
             " values.  The target value is a regular-expression for"
             " matching against the specified header.  The match is done"
             " disregarding letter case.  Lines beginning with '#' are"
	     " ignored as comments."
             "<p>For example:<pre>to: .*@public.com </pre> says"
             " to hold all postings with a <em>to</em> mail header"
             " containing '@public.com' anywhere among the addresses."
             "<p>Note that leading whitespace is trimmed from the"
             " regexp.  This can be circumvented in a number of ways, eg"
             " by escaping or bracketing it."
	     "<p> See also the <em>forbidden_posters</em> option for"
	     " a related mechanism."),
            ]

	config_info['nondigest'] = [
            "Policies concerning immediately delivered list traffic.",

	    ('nondigestable', mm_cfg.Toggle, ('No', 'Yes'), 1,
	     'Can subscribers choose to receive mail immediately,'
	     ' rather than in batched digests?'),

	    ('msg_header', mm_cfg.Text, (4, 55), 0,
	     'Header added to mail sent to regular list members',

             "Text prepended to the top of every immediately-delivery"
             " message.  <p>" + mm_err.MESSAGE_DECORATION_NOTE),
	    
	    ('msg_footer', mm_cfg.Text, (4, 55), 0,
	     'Footer added to mail sent to regular list members',

             "Text appended to the bottom of every immediately-delivery"
             " message.  <p>" + mm_err.MESSAGE_DECORATION_NOTE),
	    ]

	config_info['bounce'] = Bouncer.GetConfigInfo(self)
	return config_info

    def Create(self, name, admin, crypted_password):
	if name in mm_utils.list_names():
	    raise ValueError, 'List %s already exists.' % name
	else:
	    mm_utils.MakeDirTree(os.path.join(mm_cfg.LIST_DATA_DIR, name))
	self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
	self._internal_name = name
	self.Lock()
	self.InitVars(name, admin, crypted_password)
	self._ready = 1
	self.InitTemplates()
	self.Save()
	self.CreateFiles()

    def CreateFiles(self):
	# Touch these files so they have the right dir perms no matter what.
	# A "just-in-case" thing.  This shouldn't have to be here.
	ou = os.umask(002)
	try:
	    import mm_archive
## 	    open(os.path.join(self._full_path,
## 			      mm_archive.ARCHIVE_PENDING), "a+").close()
## 	    open(os.path.join(self._full_path,
## 			      mm_archive.ARCHIVE_RETAIN), "a+").close()
	    open(os.path.join(mm_cfg.LOCK_DIR, '%s.lock' % 
			      self._internal_name), 'a+').close()
	    open(os.path.join(self._full_path, "next-digest"), "a+").close()
	    open(os.path.join(self._full_path, "next-digest-topics"),
		 "a+").close()
	finally:
	    os.umask(ou)
	
    def Save(self):
	# If more than one client is manipulating the database at once, we're
	# pretty hosed.  That's a good reason to make this a daemon not a
	# program.
	self.IsListInitialized()
	ou = os.umask(002)
	try:
	    file = open(os.path.join(self._full_path, 'config.db'), 'w')
	finally:
	    os.umask(ou)
	dict = {}
	for (key, value) in self.__dict__.items():
	    if key[0] <> '_':
		dict[key] = value
	marshal.dump(dict, file)
	file.close()

    def Load(self):
	self.Lock()
	try:
	    file = open(os.path.join(self._full_path, 'config.db'), 'r')
	except IOError:
	    raise mm_cfg.MMBadListError, 'Failed to access config info'
	try:
	    dict = marshal.load(file)
	except (EOFError, ValueError, TypeError):
	    raise mm_cfg.MMBadListError, 'Failed to unmarshal config info'
	for (key, value) in dict.items():
	    setattr(self, key, value)
	file.close()
	self._ready = 1
	self.CheckValues()
	self.CheckVersion(dict)

    def LogMsg(self, kind, msg, *args):
	"""Append a message to the log file for messages of specified kind."""
	# For want of a better fallback,  we use sys.stderr if we can't get
	# a log file.  We need a better way to warn of failed log access...
	if self._log_files.has_key(kind):
	    logf = self._log_files[kind]
	else:
	    logf = self._log_files[kind] = mm_utils.StampedLogger(kind)
 	logf.write("%s\n" % (msg % args))
	logf.flush()

    def CheckVersion(self, stored_state):
        """Migrate prior version's state to new structure, if changed."""
	if self.data_version == mm_cfg.VERSION:
	    return
	else:
            from versions import Update
            Update(self, stored_state)

	self.data_version = mm_cfg.VERSION
	self.Save()

    def CheckValues(self):
	"""Normalize selected values to known formats."""
	if self.web_page_url and  self.web_page_url[-1] != '/':
	    self.web_page_url = self.web_page_url + '/'

    def IsListInitialized(self):
	if not self._ready:
	    raise mm_err.MMListNotReady

    def AddMember(self, name, password, digest=0, web_subscribe=0):
	self.IsListInitialized()
	# Remove spaces... it's a common thing for people to add...
	name = string.join(string.split(string.lower(name)), '')

	# Validate the e-mail address to some degree.
	if not mm_utils.ValidEmail(name):
            raise mm_err.MMBadEmailError
	if self.IsMember(name):
            raise mm_err.MMAlreadyAMember

	if digest and not self.digestable:
            raise mm_err.MMCantDigestError
	elif not digest and not self.nondigestable:
            raise mm_err.MMMustDigestError

        if self.open_subscribe:
            if (web_subscribe and self.web_subscribe_requires_confirmation):
                if self.web_subscribe_requires_confirmation == 1:
                    # Requester confirmation required.
                    raise mm_err.MMWebSubscribeRequiresConfirmation
                else:
                    # Admin approval required.
                    self.AddRequest('add_member', digest, name, password)
            else:
                # No approval required.
                self.ApprovedAddMember(name, password, digest)
        else:
            # Blanket admin approval requred...
            self.AddRequest('add_member', digest, name, password)

    def ApprovedAddMember(self, name, password, digest, noack=0):
        # XXX klm: It *might* be nice to leave the case of the name alone,
        #          but provide a common interface that always returns the
        #          lower case version for computations.
        name = string.lower(name)
	if self.IsMember(name):
	    raise mm_err.MMAlreadyAMember
	if digest:
	    self.digest_members.append(name)
            kind = " (D)"
	else:
	    self.members.append(name)
            kind = ""
        self.LogMsg("subscribe", "%s: new%s %s",
                    self._internal_name, kind, name)
	self.passwords[name] = password
	self.Save()
        if not noack:
            self.SendSubscribeAck(name, password, digest)

    def DeleteMember(self, name, whence=None):
	self.IsListInitialized()
# FindMatchingAddresses *should* never return more than 1 address.
# However, should log this, just to make sure.
	aliases = mm_utils.FindMatchingAddresses(name, self.members + 
						 self.digest_members)
	if not len(aliases):
	    raise mm_err.MMNoSuchUserError

	def DoActualRemoval(alias, me=self):
	    kind = "(unfound)"
	    try:
		del me.passwords[alias]
	    except KeyError: 
		pass
	    if me.user_options.has_key(alias):
		del me.user_options[alias]
	    try:
		me.members.remove(alias)
		kind = "regular"
	    except ValueError:
		pass
	    try:
		me.digest_members.remove(alias)
		kind = "digest"
	    except ValueError:
		pass

	map(DoActualRemoval, aliases)
	if self.goodbye_msg and len(self.goodbye_msg):
	    self.SendUnsubscribeAck(name)
	self.ClearBounceInfo(name)
	self.Save()
        if whence: whence = "; %s" % whence
        else: whence = ""
        self.LogMsg("subscribe", "%s: deleted %s%s",
                    self._internal_name, name, whence)

    def IsMember(self, address):
	return len(mm_utils.FindMatchingAddresses(address, self.members +
						    self.digest_members))

    def HasExplicitDest(self, msg):
	"""True if list name or any acceptable_alias is included among the
        to or cc addrs."""
	# Note that qualified host can be different!  This allows, eg, for
        # relaying from remote lists that have the same name.  Still
        # stringent, but offers a way to provide for remote exploders.
	lowname = string.lower(self.real_name)
        recips = []
        # First check all dests against simple name:
	for recip in msg.getaddrlist('to') + msg.getaddrlist('cc'):
            curr = string.lower(string.split(recip[1], '@')[0])
	    if lowname == curr:
		return 1
            recips.append(curr)
        # ... and only then try the regexp acceptable aliases.
        for recip in recips:
            for alias in string.split(self.acceptable_aliases, '\n'):
                stripped = string.strip(alias)
                if stripped and re.match(stripped, recip):
                    return 1
	return 0

    def parse_matching_header_opt(self):
	"""Return a list of triples [(field name, regex, line), ...]."""
	# - Blank lines and lines with '#' as first char are skipped.
	# - Leading whitespace in the matchexp is trimmed - you can defeat
	#   that by, eg, containing it in gratuitous square brackets.
	all = []
	for line in string.split(self.bounce_matching_headers, '\n'):
	    stripped = string.strip(line)
	    if not stripped or (stripped[0] == "#"):
		# Skip blank lines and lines *starting* with a '#'.
		continue
	    else:
		try:
		    h, e = re.split(":[ 	]*", line)
		    all.append((h, e, line))
		except ValueError:
		    # Whoops - some bad data got by:
		    self.LogMsg("config", "%s - "
				"bad bounce_matching_header line %s"
				% (self.real_name, `line`))
	return all


    def HasMatchingHeader(self, msg):
	"""True if named header field (case-insensitive matches regexp.

	Case insensitive.

	Returns constraint line which matches or empty string for no
	matches."""
	
	pairs = self.parse_matching_header_opt()

	for field, matchexp, line in pairs:
	    fragments = msg.getallmatchingheaders(field)
	    subjs = []
	    l = len(field)
	    for f in fragments:
		# Consolidate header lines, stripping header name & whitespace.
		if (len(f) > l
		    and f[l] == ":"
		    and string.lower(field) == string.lower(f[0:l])):
		    # Non-continuation line - trim header name:
		    subjs.append(f[l+1:])
		elif not subjs:
		    # Whoops - non-continuation that matches?
		    subjs.append(f)
		else:
		    # Continuation line.
		    subjs[-1] = subjs[-1] + f
	    for s in subjs:
		if re.search(matchexp, s, re.I):
		    return line
	return 0

#msg should be an IncomingMessage object.
    def Post(self, msg, approved=0):
	self.IsListInitialized()
        # Be sure to ExtractApproval, whether or not flag is already set!
        msgapproved = self.ExtractApproval(msg)
        if not approved:
            approved = msgapproved
	sender = msg.GetSender()
	# If it's the admin, which we know by the approved variable,
	# we can skip a large number of checks.
	if not approved:
            from_lists = msg.getallmatchingheaders('x-beenthere')
            if self.GetListEmail() in from_lists:
                self.AddRequest('post', mm_utils.SnarfMessage(msg),
                                mm_err.LOOPING_POST,
                                msg.getheader('subject'))
	    if len(self.forbidden_posters):
		addrs = mm_utils.FindMatchingAddresses(sender,
						       self.forbidden_posters)
		if len(addrs):
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    mm_err.FORBIDDEN_SENDER_MSG,
				    msg.getheader('subject'))
	    if len(self.posters):
		addrs = mm_utils.FindMatchingAddresses(sender, self.posters)
		if not len(addrs):
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    'Only approved posters may post without '
				    'moderator approval.',
				    msg.getheader('subject'))
	    elif self.moderated:
		self.AddRequest('post', mm_utils.SnarfMessage(msg),
				mm_err.MODERATED_LIST_MSG,
				msg.getheader('subject'))
	    if self.member_posting_only and not self.IsMember(sender):
		self.AddRequest('post', mm_utils.SnarfMessage(msg),
				'Postings from member addresses only.',
				msg.getheader('subject'))
	    if self.max_num_recipients > 0:
		recips = []
		toheader = msg.getheader('to')
		if toheader:
		    recips = recips + string.split(toheader, ',')
		ccheader = msg.getheader('cc')
		if ccheader:
		    recips = recips + string.split(ccheader, ',')
		if len(recips) > self.max_num_recipients:
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    'Too many recipients.',
				    msg.getheader('subject'))
 	    if (self.require_explicit_destination and
 		  not self.HasExplicitDest(msg)):
 		self.AddRequest('post', mm_utils.SnarfMessage(msg),
 				mm_err.IMPLICIT_DEST_MSG,
				msg.getheader('subject'))
 	    if self.bounce_matching_headers:
		triggered = self.HasMatchingHeader(msg)
		if triggered:
		    # Darn - can't include the matching line for the admin
		    # message because the info would also go to the sender.
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    mm_err.SUSPICIOUS_HEADER_MSG,
				    msg.getheader('subject'))
	    if self.max_message_size > 0:
		if len(msg.body)/1024. > self.max_message_size:
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    'Message body too long (>%dk)' % 
				    self.max_message_size,
				    msg.getheader('subject'))
	# Prepend the subject_prefix to the subject line.
	subj = msg.getheader('subject')
	prefix = self.subject_prefix
	if not subj:
	    msg.SetHeader('Subject', '%s(no subject)' % prefix)
	elif not re.match("(re:? *)?" + re.escape(self.subject_prefix),
			  subj, re.I):
	    msg.SetHeader('Subject', '%s%s' % (prefix, subj))

	if self.digestable:
	    self.SaveForDigest(msg)
	if self.archive:
	    self.ArchiveMail(msg)

	dont_send_to_sender = 0
	ack_post = 0
	# Try to get the address the list thinks this sender is
	sender = self.FindUser(msg.GetSender())
	if sender:
	    if self.GetUserOption(sender, mm_cfg.DontReceiveOwnPosts):
		dont_send_to_sender = 1
	    if self.GetUserOption(sender, mm_cfg.AcknowlegePosts):
		ack_post = 1
	# Deliver the mail.
	recipients = self.members[:] 
	if dont_send_to_sender:
	    recipients.remove(sender)
	def DeliveryEnabled(x, s=self, v=mm_cfg.DisableDelivery):
	    return not s.GetUserOption(x, v)
	recipients = filter(DeliveryEnabled, recipients)
	self.DeliverToList(msg, recipients,
			   self.msg_header % self.__dict__,
			   self.msg_footer % self.__dict__)
	if ack_post:
	    self.SendPostAck(msg, sender)
	self.last_post_time = time.time()
	self.post_id = self.post_id + 1
	self.Save()

    def Locked(self):
        try:
            return self._lock_file and 1
        except AttributeError:
            return 0

    def Lock(self):
	try:
	    if self._lock_file:
		return
	except AttributeError:
	    return
	ou = os.umask(0)
	try:
	    self._lock_file = posixfile.open(
		os.path.join(mm_cfg.LOCK_DIR, '%s.lock' % self._internal_name),
		'a+')
	finally:
	    os.umask(ou)
	self._lock_file.lock('w|', 1)
    
    def Unlock(self):
	self._lock_file.lock('u')
	self._lock_file.close()
	self._lock_file = None

    def __repr__(self):
	if self.Locked(): status = " (locked)"
	else: status = ""
	return ("<%s.%s %s%s at %s>"
		% (self.__module__, self.__class__.__name__,
		   `self._internal_name`, status, hex(id(self))[2:]))
