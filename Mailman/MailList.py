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

Mixes in many task-specific classes.
"""

import sys
import os
import marshal
import string
import errno
import re
from types import StringType, IntType, DictType

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import LockFile

# base classes
from Mailman.pythonlib.StringIO import StringIO
from Mailman.ListAdmin import ListAdmin
from Mailman.Deliverer import Deliverer
from Mailman.MailCommandHandler import MailCommandHandler 
from Mailman.HTMLFormatter import HTMLFormatter 
from Mailman.Archiver import Archiver
from Mailman.Digester import Digester
from Mailman.SecurityManager import SecurityManager
from Mailman.Bouncer import Bouncer
from Mailman.GatewayManager import GatewayManager
from Mailman.Logging.StampedLogger import StampedLogger



# Note: 
# an _ in front of a member variable for the MailList class indicates
# a variable that does not save when we marshal our state.

# Use mixins here just to avoid having any one chunk be too large.

class MailList(MailCommandHandler, HTMLFormatter, Deliverer, ListAdmin, 
	       Archiver, Digester, SecurityManager, Bouncer, GatewayManager):
    def __init__(self, name=None, lock=1):
        if name and name not in Utils.list_names():
		raise Errors.MMUnknownListError, 'list not found: %s' % name
	MailCommandHandler.__init__(self)
        self.InitTempVars(name, lock)
	if name:
	    self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
	    self.Load()

    def __del__(self):
        try:
            for f in self._log_files.values():
                f.close()
            self.Unlock()
        except AttributeError:
            # List may not have gotten far enough to have proper _log_files or
            # lock object!
            pass

    def GetMembers(self):
        """returns a list of the members. (all lowercase)"""
        return self.members.keys()
    
    def GetDigestMembers(self):
        """returns a list of digest members. (all lowercase)"""
        return self.digest_members.keys()

    def GetDeliveryMembers(self):
        """returns a list of the members with username case preserved."""
        res = []
        for k, v in self.members.items():
            if type(v) is StringType:
                res.append(v)
            else:
                res.append(k)
        return res

    def GetDigestDeliveryMembers(self):
        """returns a list of the members with username case preserved."""
        res = []
        for k,v in self.digest_members.items():
            if type(v) is StringType:
                res.append(v)
            else:
                res.append(k)
        return res

    def __AddMember(self, addr, digest):
        """adds the appropriate data to the internal members dict.

        If the username has upercase letters in it, then the value
        in the members dict is the case preserved address, otherwise,
        the value is 0.
        """
        if Utils.LCDomain(addr) == string.lower(addr):
            if digest:
                self.digest_members[addr] = 0
            else:
                self.members[addr] = 0
        else:
            if digest:
                self.digest_members[string.lower(addr)] = addr
            else:
                self.members[string.lower(addr)] = addr

    def GetAdminEmail(self):
        return '%s-admin@%s' % (self._internal_name, self.host_name)

    def GetMemberAdminEmail(self, member):
        """Usually the member addr, but modified for umbrella lists.

        Umbrella lists have other mailing lists as members, and so admin stuff
        like confirmation requests and passwords must not be sent to the
        member addresses - the sublists - but rather to the administrators of
        the sublists.  This routine picks the right address, considering
        regular member address to be their own administrative addresses.

        """
        if not self.umbrella_list:
            return member
        else:
            acct, host = tuple(string.split(member, '@'))
            return "%s%s@%s" % (acct, self.umbrella_member_suffix, host)

    def GetUserSubscribedAddress(self, member):
        """Return the member's case preserved address.
        """
        member = string.lower(member)
        cpuser = self.members.get(member)
        if type(cpuser) == IntType:
            return member
        elif type(cpuser) == StringType:
            return cpuser
        cpuser = self.digest_members.get(member)
        if type(cpuser) == IntType:
            return member
        elif type(cpuser) == StringType:
            return cpuser
        return None

    def GetUserCanonicalAddress(self, member):
        """Return the member's address lower cased."""
        cpuser = self.GetUserSubscribedAddress(member)
        if cpuser is not None:
            return string.lower(cpuser)
        return None

    def GetRequestEmail(self):
	return '%s-request@%s' % (self._internal_name, self.host_name)

    def GetListEmail(self):
	return '%s@%s' % (self._internal_name, self.host_name)

    def GetListIdentifier(self):
        """Return the unique (RFC draft-chandhok-listid-02) identifier."""
        return ("%s <%s.%s>" %
                (self.description, self._internal_name, self.host_name))

    def GetRelativeScriptURL(self, script_name):
	prefix = '../' * Utils.GetNestingLevel()
        return '%s%s%s/%s' % (prefix, script_name, mm_cfg.CGIEXT,
                              self._internal_name)

    def GetAbsoluteScriptURL(self, script_name):
        if self.web_page_url:
            prefix = self.web_page_url
        else:
            prefix = mm_cfg.DEFAULT_URL
        while prefix[-1] == "/":
            prefix = prefix[:-1]
        return "%s/%s%s/%s" % (prefix, script_name, mm_cfg.CGIEXT,
                               self._internal_name)

    def GetAbsoluteOptionsURL(self, addr, obscured=0):
        # address could come in case-preserved
        addr = string.lower(addr)
	options = self.GetAbsoluteScriptURL('options')
        if obscured:
            treated = Utils.ObscureEmail(addr, for_text=0)
        else:
            treated = addr
        return "%s/%s" % (options, treated)

    def GetUserOption(self, user, option):
        """Return user's setting for option, defaulting to 0 if no settings."""
        user = self.GetUserCanonicalAddress(user)
	if option == mm_cfg.Digests:
	    return self.digest_members.has_key(user)
	if not self.user_options.has_key(user):
	    return 0
	return not not self.user_options[user] & option

    def SetUserOption(self, user, option, value, save_list=1):
        user = self.GetUserCanonicalAddress(user)
	if not self.user_options.has_key(user):
	    self.user_options[user] = 0
	if value:
	    self.user_options[user] = self.user_options[user] | option
	else:
	    self.user_options[user] = self.user_options[user] & ~(option)
	if not self.user_options[user]:
	    del self.user_options[user]
	if save_list:
            self.Save()

    # Here are the rules for the three dictionaries self.members,
    # self.digest_members, and self.passwords:
    #
    # The keys of all these dictionaries are the lowercased version of the
    # address.  This makes finding a user very quick: just lowercase the name
    # you're matching against, and do a has_key() or get() on first
    # self.members, then if that returns false, self.digest_members
    #
    # The value of the key in self.members and self.digest_members is either
    # the integer 0, meaning the user was subscribed with an all-lowercase
    # address, or a string which would be the address with the username part
    # case preserved.  Note that for Mailman versions before 1.0b11, the value 
    # could also have been the integer 1.  This is a bug that was caused when
    # a user switched from regular to/from digest membership.  If this
    # happened, you're screwed because there's no way to recover the case
    # preserved address. :-(
    #
    # The keys for self.passwords is also lowercase, although for versions of
    # Mailman before 1.0b11, this was not always true.  1.0b11 has a hack in
    # Load() that forces the keys to lowercase.  The value for the keys in
    # self.passwords is, of course the password in plain text.
    
    def FindUser(self, email):
        """Return the lowercased version of the subscribed email address.

        If email is not subscribed, either as a regular member or digest
        member, None is returned.  If they are subscribed, the return value is 
        guaranteed to be lowercased.
        """
        # shortcut
        lcuser = self.GetUserCanonicalAddress(email)
        if lcuser is not None:
            return lcuser
	matches = Utils.FindMatchingAddresses(email,
                                              self.members,
                                              self.digest_members)
        # sadly, matches may or may not be case preserved
	if not matches or not len(matches):
	    return None
	return string.lower(matches[0])

    def InitTempVars(self, name, lock):
        """Set transient variables of this and inherited classes."""
	self.__createlock_p = lock
	self.__lock = LockFile.LockFile(
            os.path.join(mm_cfg.LOCK_DIR, name or '<site>') + '.lock',
            # TBD: is this a good choice of lifetime?
            lifetime = 60)
	self._internal_name = name
	self._ready = 0
	self._log_files = {}		# 'class': log_file_obj
	if name:
	    self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
        ListAdmin.InitTempVars(self)

    def InitVars(self, name=None, admin='', crypted_password=''):
        """Assign default values - some will be overriden by stored state."""
	# Non-configurable list info 
	if name:
	  self._internal_name = name

	# Must save this state, even though it isn't configurable
	self.volume = 1
	self.members = {} # self.digest_members is initted in mm_digest
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
        self.admin_notify_mchanges = \
                mm_cfg.DEFAULT_ADMIN_NOTIFY_MCHANGES
	self.moderated = mm_cfg.DEFAULT_MODERATED
	self.require_explicit_destination = \
		mm_cfg.DEFAULT_REQUIRE_EXPLICIT_DESTINATION
        self.acceptable_aliases = mm_cfg.DEFAULT_ACCEPTABLE_ALIASES
	self.umbrella_list = mm_cfg.DEFAULT_UMBRELLA_LIST
	self.umbrella_member_suffix = \
                mm_cfg.DEFAULT_UMBRELLA_MEMBER_ADMIN_SUFFIX
	self.send_reminders = mm_cfg.DEFAULT_SEND_REMINDERS
    	self.send_welcome_msg = mm_cfg.DEFAULT_SEND_WELCOME_MSG
	self.bounce_matching_headers = \
		mm_cfg.DEFAULT_BOUNCE_MATCHING_HEADERS
        self.anonymous_list = mm_cfg.DEFAULT_ANONYMOUS_LIST
	self.real_name = '%s%s' % (string.upper(self._internal_name[0]), 
				   self._internal_name[1:])
	self.description = ''
	self.info = ''
	self.welcome_msg = ''
	self.goodbye_msg = ''
	self.subscribe_policy = mm_cfg.DEFAULT_SUBSCRIBE_POLICY
	self.private_roster = mm_cfg.DEFAULT_PRIVATE_ROSTER
	self.obscure_addresses = mm_cfg.DEFAULT_OBSCURE_ADDRESSES
	self.member_posting_only = mm_cfg.DEFAULT_MEMBER_POSTING_ONLY
	self.host_name = mm_cfg.DEFAULT_HOST_NAME
        self.admin_member_chunksize = mm_cfg.DEFAULT_ADMIN_MEMBER_CHUNKSIZE

	# Analogs to these are initted in Digester.InitVars
	self.nondigestable = mm_cfg.DEFAULT_NONDIGESTABLE

	Digester.InitVars(self) # has configurable stuff
	SecurityManager.InitVars(self, crypted_password)
	Archiver.InitVars(self) # has configurable stuff
	ListAdmin.InitVars(self)
	Bouncer.InitVars(self)
	GatewayManager.InitVars(self)
	HTMLFormatter.InitVars(self)

	# These need to come near the bottom because they're dependent on
	# other settings.
	self.subject_prefix = mm_cfg.DEFAULT_SUBJECT_PREFIX % self.__dict__
	self.msg_header = mm_cfg.DEFAULT_MSG_HEADER
	self.msg_footer = mm_cfg.DEFAULT_MSG_FOOTER

    def GetConfigInfo(self):
	config_info = {}
	config_info['digest'] = Digester.GetConfigInfo(self)
	config_info['archive'] = Archiver.GetConfigInfo(self)
	config_info['gateway'] = GatewayManager.GetConfigInfo(self)

        # XXX: Should this text be migrated into the templates dir?
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

             "This description is used when the mailing list is listed with"
             " other mailing lists, or in headers, and so forth.  It should"
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
             " posted to the list, to distinguish mailing list messages in"
             " in mailbox summaries.  Brevity is premium here, it's ok"
             " to shorten long mailing list names to something more concise,"
             " as long as it still identifies the mailing list."),

	    ('welcome_msg', mm_cfg.Text, (4, 50), 0,
	     'List-specific text prepended to new-subscriber welcome message',

             "This value, if any, will be added to the front of the"
             " new-subscriber welcome message.  The rest of the"
             " welcome message already describes the important addresses"
             " and URLs for the mailing list, so you don't need to include"
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

            ('administrivia', mm_cfg.Radio, ('No', 'Yes'), 0,
             "(Administrivia filter) Check postings and intercept ones"
             " that seem to be administrative requests?",

             "Administrivia tests will check postings to see whether"
             " it's really meant as an administrative request (like"
             " subscribe, unsubscribe, etc), and will add it to the"
             " the administrative requests queue, notifying the "
             " administrator of the new request, in the process. "),


	    ('umbrella_list', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Send password reminders to, eg, "-owner" address instead of'
	     ' directly to user.',

	     "Set this to yes when this list is intended to cascade only to"
	     " other mailing lists.  When set, meta notices like confirmations"
             " and password reminders will be directed to an address derived"
             " from the member\'s address - it will have the value of"
             ' \"umbrella_member_suffix\" appended to the'
             " member\'s account name."),

	    ('umbrella_member_suffix', mm_cfg.String, 8, 0,
	     'Suffix for use when this list is an umbrella for other lists,'
             ' according to setting of previous "umbrella_list" setting.',

	     'When \"umbrella_list\" is set to indicate that this list has'
             " other mailing lists as members, then administrative notices"
             " like confirmations and password reminders need to not be sent"
             " to the member list addresses, but rather to the owner of those"
             " member lists.  In that case, the value of this setting is"
             " appended to the member\'s account name for such notices."
             " \'-owner\' is the typical choice.  This setting has no"
             ' effect when \"umbrella_list\" is \"No\".'),

	    ('send_reminders', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Send monthly password reminders or no? Overrides the previous '
	     'option.'),

	    ('send_welcome_msg', mm_cfg.Radio, ('No', 'Yes'), 0, 
	     'Send welcome message when people subscribe?',
	     "Turn this on only if you plan on subscribing people manually "
	     "and don't want them to know that you did so.  This option "
	     "is most useful for transparently migrating lists from "
	     "some other mailing list manager to Mailman."),


	    ('admin_immed_notify', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Should administrator get immediate notice of new requests, '
	     'as well as daily notices about collected ones?',

             "List admins are sent daily reminders of pending admin approval"
             " requests, like subscriptions to a moderated list or postings"
	     " that are being held for one reason or another.  Setting this"
	     " option causes notices to be sent immediately on the arrival"
	     " of new requests, as well."),

            ('admin_notify_mchanges', mm_cfg.Radio, ('No', 'Yes'), 0,
             'Should administrator get notices of subscribes/unsubscribes?'),
            
	    ('dont_respond_to_post_requests', mm_cfg.Radio, ('Yes', 'No'), 0,
	     'Send mail to poster when their posting is held for approval?',

             "Approval notices are sent when mail triggers certain of the"
             " limits <em>except</em> routine list moderation and spam"
	     " filters, for which notices are <em>not</em> sent.  This"
	     " option overrides ever sending the notice."),

	    ('max_message_size', mm_cfg.Number, 5, 0,
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
             " list.  It is also used in the listinfo overview of mailing"
             " lists"
             " to identify whether or not this list resides on the virtual"
             " host identified by the overview URL - if this value is found"
             " (anywhere) in the URL, then this list is considered to be"
             " on that virtual host, and if not, then it is excluded from"
             " the listing.  Note that you should use the \'advertised\'"
             " privacy option to inhibit any listing of the host."),
          ]
        if mm_cfg.ALLOW_OPEN_SUBSCRIBE:
            sub_cfentry = ('subscribe_policy', mm_cfg.Radio,
                           ('none', 'confirm', 'require approval',
                            'confirm+approval'),  0, 
                           "What steps are required for subscription?<br>",
                           "None - no verification steps (<em>Not"
                           " Recommended </em>)<br>"
                           "confirm (*) - email confirmation step"
                           " required <br>"
                           "require approval - require list administrator"
                           " approval for subscriptions <br>"
                           "confirm+approval - both confirm and approve"
                           
                           "<p> (*) when someone requests a subscription,"
                           " mailman sends them a notice with a unique"
                           " subscription request number that they must"
                           " reply to in order to subscribe.<br> This"
                           " prevents mischievous (or malicious) people"
                           " from creating subscriptions for others"
                           " without their consent."
                           )
        else:
            sub_cfentry = ('subscribe_policy', mm_cfg.Radio,
                           ('confirm', 'require approval',
                            'confirm+approval'),  1,
                           "What steps are required for subscription?<br>",
                           "confirm (*) - email confirmation required <br>"
                           "require approval - require list administrator"
                           " approval for subscriptions <br>"
                           "confirm+approval - both confirm and approve"
                           "<p> (*) when someone requests a subscription,"
                           " mailman sends them a notice with a unique"
                           " subscription request number that they must"
                           " reply to in order to subscribe.<br> This"
                           " prevents mischievous (or malicious) people"
                           " from creating subscriptions for others"
                           " without their consent."
                           )


        config_info['privacy'] = [
            "List access policies, including anti-spam measures,"
            " covering members and outsiders."
            '  (See also the <a href="%s/archive">Archival Options'
            ' section</a> for separate archive-privacy settings.)'
            % (self.GetRelativeScriptURL('admin')),

	    "Subscribing",

	    ('advertised', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Advertise this list when people ask what lists are on '
	     'this machine?'),

            sub_cfentry,
            
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
	     'Must posts be approved by an administrator?'),

	    ('member_posting_only', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Restrict posting privilege to list members?'
             ' (<i>member_posting_only</i>)',

             "Use this option if you want to restrict posting to list members."
             " If you want list members to be able to"
             " post, plus a handful of other posters, see the <i> posters </i>"
             " setting below"),

	    ('posters', mm_cfg.EmailList, (5, 30), 1,
             'Addresses of members accepted for posting to this'
             ' list without implicit approval requirement. (See'
             ' "Restrict ... to list members"'
             ' for whether or not this is in addition to allowing posting'
             ' by list members',

             "Adding entries here will have one of two effects,"
             " according to whether another option restricts posting to"
             " members. <ul>"
             " <li> If <i>member_posting_only</i> is 'yes', then entries"
             " added here will have posting privilege in addition to"
             " list members."
             " <li> If <i>member_posting_only</i> is 'no', then <em>only</em>"
             " the posters listed here will be able to post without admin"
             " approval. </ul>"),

            "Spam-specific posting filters",

 	    ('require_explicit_destination', mm_cfg.Radio, ('No', 'Yes'), 0,
 	     'Must posts have list named in destination (to, cc) field'
             ' (or be among the acceptable alias names, specified below)?',

             "Many (in fact, most) spams do not explicitly name their myriad"
             " destinations in the explicit destination addresses - in fact,"
             " often the to field has a totally bogus address for"
             " obfuscation.  The constraint applies only to the stuff in"
             " the address before the '@' sign, but still catches all such"
             " spams."
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
             " mailing lists and relays while the constraint is still"
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

	    ('anonymous_list', mm_cfg.Radio, ('No', 'Yes'), 0,
	      'Hide the sender of a message, replacing it with the list '
	      'address (Removes From, Sender and Reply-To fields)'),
	         
            ]

	config_info['nondigest'] = [
            "Policies concerning immediately delivered list traffic.",

	    ('nondigestable', mm_cfg.Toggle, ('No', 'Yes'), 1,
	     'Can subscribers choose to receive mail immediately,'
	     ' rather than in batched digests?'),

	    ('msg_header', mm_cfg.Text, (4, 55), 0,
	     'Header added to mail sent to regular list members',

             "Text prepended to the top of every immediately-delivery"
             " message.  <p>" + Errors.MESSAGE_DECORATION_NOTE),
	    
	    ('msg_footer', mm_cfg.Text, (4, 55), 0,
	     'Footer added to mail sent to regular list members',

             "Text appended to the bottom of every immediately-delivery"
             " message.  <p>" + Errors.MESSAGE_DECORATION_NOTE),
	    ]

	config_info['bounce'] = Bouncer.GetConfigInfo(self)
	return config_info

    def Create(self, name, admin, crypted_password):
	if name in Utils.list_names():
	    raise ValueError, 'List %s already exists.' % name
        Utils.ValidateEmail(admin)
        Utils.MakeDirTree(os.path.join(mm_cfg.LIST_DATA_DIR, name))
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
        # copy all public attributes to marshalable dictionary
        dict = {}
	for key, value in self.__dict__.items():
	    if key[0] <> '_':
		dict[key] = value
        # we want to write this dict in a marshal, but be especially paranoid
        # about how we write the config.db, so we'll be as robust as possible
        # in the face of, e.g. disk full errors.  The idea is that we want to
        # guarantee that config.db is always valid.  The old way had the bad
        # habit of writing an incomplete file, which happened to be a valid
        # (but bogus) marshal.
        fname = os.path.join(self._full_path, 'config.db')
        fname_tmp = fname + '.tmp.' + `os.getpid()`
        fname_last = fname + ".last"
        # Make config.db unreadable by `other', as it contains all the
        # list members' passwords (in clear text).
        omask = os.umask(007)
        try:
            try:
                fp = open(fname_tmp, 'w')
                marshal.dump(dict, fp)
                fp.close()
            except IOError, status:
                os.unlink(fname_tmp)
                self.LogMsg('error',
                            'Failed config.db file write, retaining old state'
                            '\n %s' % `status.args`)
                Utils.reraise()
            # Now do config.db.tmp.xxx -> config.db -> config.db.last
            # rotation -- safely.
            try:
                # might not exist yet
                os.unlink(fname_last)
            except os.error, (code, msg):
                if code <> errno.ENOENT:
                    Utils.reraise()
            try:
                # might not exist yet
                os.link(fname, fname_last)
            except os.error, (code, msg):
                if code <> errno.ENOENT:
                    Utils.reraise()
            os.rename(fname_tmp, fname)
        finally:
            os.umask(omask)
        self.CheckHTMLArchiveDir()
        self.SaveRequestsDb()

    def Load(self, check_version = 1):
        if self.__createlock_p:
            try:
                self.Lock()
            except LockFile.AlreadyLockedError:
                pass
	try:
	    file = open(os.path.join(self._full_path, 'config.db'), 'r')
	except IOError:
	    raise Errors.MMBadListError, 'Failed to access config info'
	try:
	    dict = marshal.load(file)
            if type(dict) <> DictType:
                raise Errors.MMBadListError, \
                      'Unmarshaled config info is not a dictionary'
	except (EOFError, ValueError, TypeError), e:
	    raise Errors.MMBadListError, ('Failed to unmarshal config info: '
                                          + e)
	for key, value in dict.items():
	    setattr(self, key, value)
	file.close()
	self._ready = 1
        if check_version:
            self.CheckValues()
            self.CheckVersion(dict)

    def LogMsg(self, kind, msg, *args):
	"""Append a message to the log file for messages of specified kind."""
	# For want of a better fallback,  we use sys.stderr if we can't get
	# a log file.  We need a better way to warn of failed log access...
	if self._log_files.has_key(kind):
	    logf = self._log_files[kind]
	else:
	    logf = self._log_files[kind] = StampedLogger(kind)
        logf.write(msg % args + '\n')
	logf.flush()

    def CheckVersion(self, stored_state):
        """Migrate prior version's state to new structure, if changed."""
	if (self.data_version >= mm_cfg.DATA_FILE_VERSION and 
		type(self.data_version) == type(mm_cfg.DATA_FILE_VERSION)):
	    return
	else:
	    self.InitVars() # Init any new variables, 
	    self.Load(check_version = 0) # then reload the file
            from versions import Update
            Update(self, stored_state)
	    self.data_version = mm_cfg.DATA_FILE_VERSION
	self.Save()

    def CheckValues(self):
	"""Normalize selected values to known formats."""
	if self.web_page_url and  self.web_page_url[-1] != '/':
	    self.web_page_url = self.web_page_url + '/'

    def IsListInitialized(self):
	if not self._ready:
	    raise Errors.MMListNotReady

    def AddMember(self, name, password, digest=0, remote=None):
	self.IsListInitialized()
        # normalize the name, it could be of the form
        #
        # <person@place.com> User Name
        # person@place.com (User Name)
        # etc
        #
        name = Utils.ParseAddrs(name)
	# Remove spaces... it's a common thing for people to add...
	name = string.join(string.split(name), '')
        # lower case only the domain part
        name = Utils.LCDomain(name)

	# Validate the e-mail address to some degree.
	Utils.ValidateEmail(name)
	if self.IsMember(name):
            raise Errors.MMAlreadyAMember
        if name == string.lower(self.GetListEmail()):
            # Trying to subscribe the list to itself!
            raise Errors.MMBadEmailError

	if digest and not self.digestable:
            raise Errors.MMCantDigestError
	elif not digest and not self.nondigestable:
            raise Errors.MMMustDigestError

        if self.subscribe_policy == 0:
            # no confirmation or approval necessary:
            self.ApprovedAddMember(name, password, digest)
        elif self.subscribe_policy == 1 or self.subscribe_policy == 3:
            # confirmation:
            from Pending import Pending
            cookie = Pending().new(name, password, digest)
            if remote is not None:
                by = " " + remote
                remote = " from %s" % remote
            else:
                by = ""
                remote = ""
            recipient = self.GetMemberAdminEmail(name)
            text = Utils.maketext('verify.txt',
                                  {"email"      : name,
                                   "listaddr"   : self.GetListEmail(),
                                   "listname"   : self.real_name,
                                   "cookie"     : cookie,
                                   "hostname"   : remote,
                                   "requestaddr": self.GetRequestEmail(),
                                   "remote"     : remote,
                                   "listadmin"  : self.GetAdminEmail(),
                                   })
            self.SendTextToUser(
                subject=("%s -- confirmation of subscription -- request %d" % 
                         (self.real_name, cookie)),
                recipient = recipient,
                sender = self.GetRequestEmail(),
                text = text,
                add_headers = ["Reply-to: %s" % self.GetRequestEmail(),
                               "Errors-To: %s" % self.GetAdminEmail()])
            if recipient != name:
                who = "%s (%s)" % (name, string.split(recipient, '@')[0])
            else: who = name
            self.LogMsg("subscribe", "%s: pending %s %s",
                        self._internal_name,
                        who,
                        by)
            raise Errors.MMSubscribeNeedsConfirmation
        else:
            # subscription approval is required.  add this entry to the admin
            # requests database.
            self.HoldSubscription(name, password, digest)
            raise Errors.MMNeedApproval, \
                  'subscriptions to %s require administrator approval' % \
                  self.real_name

    def ProcessConfirmation(self, cookie):
        from Pending import Pending
        got = Pending().confirmed(cookie)
        if not got:
            raise Errors.MMBadConfirmation
        else:
            (email_addr, password, digest) = got
        try:
            if self.subscribe_policy == 3: # confirm + approve
                self.HoldSubscription(email_addr, password, digest)
                raise Errors.MMNeedApproval, \
                      'subscriptions to %s require administrator approval' % \
                      self.real_name
            self.ApprovedAddMember(email_addr, password, digest)
        finally:
            self.Save()

    def ApprovedAddMember(self, name, password, digest,
                          ack=None, admin_notif=None):
        res = self.ApprovedAddMembers([name], [password],
                                      digest, ack, admin_notif)
        # There should be exactly one (key, value) pair in the returned dict,
        # extract the possible exception value
        res = res.values()[0]
        if res is None:
            # User was added successfully
            return
        else:
            # Split up the exception list and reraise it here
            e, v = res
            raise e, v

    def ApprovedAddMembers(self, names, passwords, digest,
                          ack=None, admin_notif=None):
        """Subscribe members in list `names'.

        Passwords can be supplied in the passwords list.  If an empty
        password is encountered, a random one is generated and used.

        Returns a dict where the keys are addresses that were tried
        subscribed, and the corresponding values are either two-element
        tuple containing the first exception type and value that was
        raised when trying to add that address, or `None' to indicate
        that no exception was raised.

        """
        if ack is None:
            if self.send_welcome_msg:
                ack = 1
            else:
                ack = 0
        if admin_notif is None:
            if self.admin_notify_mchanges:
                admin_notif = 1
            else:
                admin_notif = 0
        if type(passwords) is type([]):
            pass
        else:
            # Type error -- ignore the original value
            passwords = [None] * len(names)
        while len(passwords) < len(names):
            passwords.append(None)
        result = {}
        dirty = 0
        for i in range(len(names)):
            try:
                # normalize the name, it could be of the form
                #
                # <person@place.com> User Name
                # person@place.com (User Name)
                # etc
                #
                name = Utils.ParseAddrs(names[i])
                Utils.ValidateEmail(name)
                name = Utils.LCDomain(name)
            except (Errors.MMBadEmailError, Errors.MMHostileAddress):
                # We don't really need the traceback object for the exception,
                # and as using it in the wrong way prevents garbage collection
                # from working smoothly, we strip it away
                result[name] = sys.exc_info()[:2]
            # WIBNI we could `continue' within `try' constructs...
            if result.has_key(name):
                continue
            if self.IsMember(name):
                result[name] = [Errors.MMAlreadyAMember, name]
                continue
            self.__AddMember(name, digest)
            self.SetUserOption(name, mm_cfg.DisableMime,
                               1 - self.mime_is_default_digest,
                               save_list=0)
            # Make sure we set a "good" password
            password = passwords[i]
            if not password:
                password = Utils.MakeRandomPassword()
            self.passwords[string.lower(name)] = password
            # An address has been added successfully, make sure the
            # list config is saved later on
            dirty = 1
            result[name] = None

        if dirty:
            self.Save()
            if digest:
                kind = " (D)"
            else:
                kind = ""
            for name in result.keys():
                Utils.Reap()
                if result[name] is None:
                    self.LogMsg("subscribe", "%s: new%s %s",
                                self._internal_name, kind, name)
                    if ack:
                        self.SendSubscribeAck(
                            name,
                            self.passwords[string.lower(name)],
                            digest)
                    if admin_notif:
                        import Message
                        txt = Utils.maketext(
                            "adminsubscribeack.txt",
                            {"mmowner": mm_cfg.MAILMAN_OWNER,
                             "admin_email": self.GetAdminEmail(),
                             "listname": self.real_name,
                             "member": name}, 1)
                        msg = Message.Message(StringIO(txt))
                        self.DeliverToOwner(msg, self.owner)
        return result

    def DeleteMember(self, name, whence=None, admin_notif=None):
	self.IsListInitialized()
        # FindMatchingAddresses *should* never return more than 1 address.
        # However, should log this, just to make sure.
	aliases = Utils.FindMatchingAddresses(name, self.members, 
                                              self.digest_members)
	if not len(aliases):
	    raise Errors.MMNoSuchUserError

	def DoActualRemoval(alias, me=self):
	    kind = "(unfound)"
	    try:
		del me.passwords[alias]
	    except KeyError: 
		pass
	    if me.user_options.has_key(alias):
		del me.user_options[alias]
	    try:
		del me.members[alias]
		kind = "regular"
	    except KeyError:
		pass
	    try:
		del me.digest_members[alias]
		kind = "digest"
	    except KeyError:
		pass

	map(DoActualRemoval, aliases)
	if self.goodbye_msg and len(self.goodbye_msg):
	    self.SendUnsubscribeAck(name)
	self.ClearBounceInfo(name)
	self.Save()
        if admin_notif is None:
            if self.admin_notify_mchanges:
                admin_notif = 1
            else:
                admin_notif = 0
	if admin_notif:
	    import Message
	    txt = Utils.maketext("adminunsubscribeack.txt",
				 {"mmowner": mm_cfg.MAILMAN_OWNER,
				  "admin_email": self.GetAdminEmail(),
				  "listname": self.real_name,
				  "member": name}, 1)
	    msg = Message.Message(StringIO(txt))
	    self.DeliverToOwner(msg, self.owner)
        if whence: whence = "; %s" % whence
        else: whence = ""
        self.LogMsg("subscribe", "%s: deleted %s%s",
                    self._internal_name, name, whence)

    def IsMember(self, address):
	return len(Utils.FindMatchingAddresses(address, self.members,
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
                try:
                    # The list alias in `stripped` is a user supplied regexp,
                    # which could be malformed.
                    if stripped and re.match(stripped, recip):
                        return 1
                except re.error:
                    # `stripped' is a malformed regexp -- try matching
                    # safely, with all non-alphanumerics backslashed:
                    if stripped and re.match(re.escape(stripped), recip):
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
		    h, e = re.split(":[ \t]*", stripped, 1)
                    try:
                        re.compile(e)
                        all.append((h, e, stripped))
                    except re.error, cause:
                        # The regexp in this line is malformed -- log it
                        # and ignore it
                        self.LogMsg("config", "%s - "
                                    "bad regexp %s [%s] "
                                    "in bounce_matching_header line %s"
                                    % (self.real_name, `e`,
                                       `cause`, `stripped`))
		except ValueError:
		    # Whoops - some bad data got by:
		    self.LogMsg("config", "%s - "
				"bad bounce_matching_header line %s"
				% (self.real_name, `stripped`))
	return all

    def HasMatchingHeader(self, msg):
	"""True if named header field (case-insensitive) matches regexp.

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
		    subjs.append(f[l+2:])
		elif not subjs:
		    # Whoops - non-continuation that matches?
		    subjs.append(f)
		else:
		    # Continuation line.
		    subjs[-1] = subjs[-1] + f
	    for s in subjs:
                # This is safe because parse_matching_header_opt only
                # returns valid regexps
		if re.search(matchexp, s, re.I):
		    return line
	return 0

    # msg should be an Message.Message object.
    def Post(self, msg):
	self.IsListInitialized()
        # TBD: this is bogus and will later be configurable
        import Mailman.Handlers.HandlerAPI
        Mailman.Handlers.HandlerAPI.process(self, msg)
	self.Save()

    def Locked(self):
        return self.__lock.locked()

    def Lock(self):
        self.__lock.lock()
    
    def Unlock(self):
        try:
            self.__lock.unlock()
        except LockFile.NotLockedError:
            pass

    def __repr__(self):
	if self.Locked():
            status = " (locked)"
	else:
            status = ""
	return ("<%s.%s %s%s at %s>" %
                (self.__module__, self.__class__.__name__,
                 `self._internal_name`, status, hex(id(self))[2:]))

    def internal_name(self):
        return self._internal_name

    def fullpath(self):
        return self._full_path
