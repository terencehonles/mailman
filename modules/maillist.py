# Notice that unlike majordomo, message headers/footers aren't going
# on until After the post has been added to the digest / archive.  I
# tried putting a footer on the bottom of each message on a majordomo
# list once, but it sucked hard, because you'd see the footer 100
# times in each digest.


import sys, os, marshal, string, posixfile, time
import mm_cfg, mm_utils, mm_err

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
	if name:
	    self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
	    # Load in the default values so that old data files aren't hosed
	    # by new versions of the program.
	    self.InitVars(name)
	    self.Load()


    def GetAdminEmail(self):
	return '%s-admin@%s' % (self._internal_name, self.host_name)

    def GetRequestEmail(self):
	return '%s-request@%s' % (self._internal_name, self.host_name)

    def GetListEmail(self):
	return '%s@%s' % (self._internal_name, self.host_name)

    def GetScriptURL(self, script_name):
	return os.path.join(self.web_page_url, '%s/%s' % 
			    (script_name, self._internal_name))


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
	matches = mm_utils.FindMatchingAddresses(email, self.members + self.digest_members)
	if not matches or not len(matches):
	    return None
	return matches[0]

    def InitVars(self, name='', admin='', crypted_password=''):
	# Non-configurable list info 
	self._internal_name = name
	self._lock_file = None
	self._mime_separator = '__--__--' 

	# Must save this state, even though it isn't configurable
	self.volume = 1
	self.members = [] # self.digest_members is inited in mm_digest
	self.data_version = mm_cfg.VERSION
	self.last_post_time = 0
	self.post_id = 1.  # Make it a float so it doesn't ever have a chance at overflow
	self.user_options = {}

	# This stuff is configurable
	self.filter_prog = ''
	self.dont_respond_to_post_requests = 0
	self.num_spawns = 5
	self.subject_prefix = ''
	self.advertised = 1
	self.max_num_recipients = 5
	self.max_message_size = 40
	self.web_page_url = mm_cfg.DEFAULT_URL   
	self.owner = [admin]
	self.reply_goes_to_list = 0
	self.posters = []
	self.bad_posters = []
	self.moderated = 0
	self.require_explicit_destination = 1
	self.real_name = '%s%s' % (string.upper(self._internal_name[0]), 
				   self._internal_name[1:])
	self.description = ''
	self.info = ''
	self.welcome_msg = None
	self.goodbye_msg = None
	self.auto_subscribe = 1
	self.closed = 0
	self.member_posting_only = 0  # Make it 1 when it works
	# Make this 1 to mean email confirmation,
	# make it 2 to mean admin confirmation
	self.web_subscribe_requires_confirmation = 2
	self.host_name = mm_cfg.DEFAULT_HOST_NAME

	# Analogs to these are initted in Digester.InitVars
	# Can we get this mailing list in non-digest format?
	self.nondigestable = 1
	self.msg_header = None
	self.msg_footer = None

	Digester.InitVars(self) # has configurable stuff
	SecurityManager.InitVars(self, crypted_password)
	HTMLFormatter.InitVars(self)
	Archiver.InitVars(self) # has configurable stuff
	ListAdmin.InitVars(self)
	Bouncer.InitVars(self)

    def GetConfigInfo(self):
	config_info = {}
	config_info['digest'] = Digester.GetConfigInfo(self)
	config_info['archive'] = Archiver.GetConfigInfo(self)

	config_info['general'] = [
	    ('real_name', mm_cfg.String, 50, 0,
	     'The public name of this list'),

	    ('owner', mm_cfg.EmailList, (3,30), 0,
	     'The list admin\'s email address '
	     '(or addresses if more than 1 admin)'),

	    ('description', mm_cfg.String, 50, 0,
	     'A one sentence description of this list'),

	    ('info', mm_cfg.Text, (7, 65), 0, 
	     'An informational paragraph about the list'),

	    ('advertised', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Advertise this mailing list when people ask what lists are on '
	     'this machine?'),

	    ('welcome_msg', mm_cfg.Text, (4, 65), 0,
	     'List specific welcome sent to new subscribers'),

	    ('goodbye_msg', mm_cfg.Text, (4, 65), 0,
	     'Text sent to people leaving the list.'
	     'If you don\'t provide text, no special message '
	     'will be sent upon unsubscribe.'),

	    ('reply_goes_to_list', mm_cfg.Radio, ('Sender', 'List'), 0,
	     'Replies to a post go to the sender or the list?'),

	    ('moderated', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Posts have to be approved by a moderator'),

 	    ('require_explicit_destination', mm_cfg.Radio, ('No', 'Yes'), 0,
 	     'Posts must have list named in destination (to, cc) field'
	     ' (anti-spam)'),

	    ('posters', mm_cfg.EmailList, (5, 30), 1,
	     'Email addresses whose posts are auto-approved '
	     '(adding anyone to this list will make this a moderated list)'),

	    ('bad_posters', mm_cfg.EmailList, (5, 30), 1,
	     'Email addresses whose posts should always be bounced until '
	     'you approve them, no matter what other options you have set'
	     ' (anti-spam)'),

	    ('closed', mm_cfg.Radio, ('Anyone', 'List members', 'No one'), 0,
	     'Who can see the subscription list'),

	    ('member_posting_only', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Only list members can send mail to the list without approval'),

	    ('auto_subscribe', mm_cfg.Radio, ('No', 'Yes'), 0,
	     'Subscribes are done automatically w/o admins approval'),

	    # If auto_subscribe is off, this is ignored, essentially.
	    ('web_subscribe_requires_confirmation', mm_cfg.Radio,
	     ('None', 'Requestor sends email', 'Admin approves'), 0,
	     'Extra confirmation for off-the-web subscribes'),

	    ('dont_respond_to_post_requests', mm_cfg.Radio,
	     ('Yes', 'No'), 0, 'Send mail to the poster when his mail '
	     'is held, waiting for approval?'),

	    ('filter_prog', mm_cfg.String, 20, 0,
	     'Program to pass text through before processing, if any? '
	     '(This would be useful for auto-stripping signatures, etc...)'),

	    ('max_num_recipients', mm_cfg.Number, 3, 0, 
	     'If there are more than this number of recipients '
	     'in the TO and CC list, require admin approval '
	     '(To prevent spams)  Make it 0 for no limit.'),

	    ('max_message_size', mm_cfg.Number, 3, 0,
	     'Maximum length in Kb of a message body. '
	     '(Make it 0 for no limit).'),

	    ('num_spawns', mm_cfg.Number, 3, 0,
	     'Number of outgoing connections to open at once '
	     '(Expert users only)'),

	    ('host_name', mm_cfg.Host, 50, 0, 'Host name this list prefers'),

	    ('web_page_url', mm_cfg.String, 50, 0,
	     'Base URL for Mailman web interface')
	    ]

	config_info['nondigest'] = [
	    ('nondigestable', mm_cfg.Toggle, ('No', 'Yes'), 1,
	     'Can subscribers choose to receive individual mail?'),

	    ('msg_header', mm_cfg.Text, (4, 65), 0,
	     'Header added to mail sent to regular list members'),
	    
	    ('msg_footer', mm_cfg.Text, (4, 65), 0,
	     'Footer added to mail sent to regular list members'),

	    ('subject_prefix', mm_cfg.String, 10, 0,
	     'Prefix to add to subject lines.  This is intended to make it '
	     'obvious to the mail reader which mail comes from the list.'),

	    ]

	config_info['bounce'] = Bouncer.GetConfigInfo(self)
	return config_info

    def Create(self, name, admin, crypted_password):
	self._internal_name = name
	self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
	if os.path.isdir(self._full_path):
	    if os.path.exists(os.path.join(self._full_path, 'config.db')):
		raise ValueError, 'List %s already exists.' % name
	else:
	    mm_utils.MakeDirTree(os.path.join(mm_cfg.LIST_DATA_DIR, name))
	self.Lock()
	self.InitVars(name, admin, crypted_password)
	self._ready = 1
	self.InitTemplates()
	self.Save()
	self.CreateFiles()

    def CreateFiles(self):
	# Touch these files so they have the right dir perms no matter what.
	# A "just-in-case" thing.  This shouldn't have to be here.
	open(os.path.join(self._full_path, "archived.mail"), "a+").close()
	open(os.path.join(mm_cfg.LOCK_DIR, '%s.lock' % 
			       self._internal_name), 'a+').close()
	open(os.path.join(self._full_path, "next-digest"), "a+").close()
	open(os.path.join(self._full_path, "next-digest-topics"), "a+").close()
	
    def Save(self):
	# If more than one client is manipulating the database at once, we're
	# pretty hosed.  That's a good reason to make this a daemon not a program.
	self.IsListInitialized()
	file = open(os.path.join(self._full_path, 'config.db'), 'w')
	dict = {}
	for (key, value) in self.__dict__.items():
	    if key[0] <> '_':
		dict[key] = value
	marshal.dump(dict, file)
	file.close()

    def Load(self):
	self.Lock()
	file = open(os.path.join(self._full_path, 'config.db'), 'r')
	dict = marshal.load(file)
	for (key, value) in dict.items():
	    setattr(self, key, value)
	file.close()
	self._ready = 1
	self.CheckVersion()

    def CheckVersion(self):
	if self.data_version == mm_cfg.VERSION:
	    return
	else:
	    pass  # This function is just here to ease upgrades in the future.

	self.data_version = mm_cfg.VERSION
	self.Save()

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
	if not digest:
	    if not self.nondigestable:
		raise mm_err.MMMustDigestError
	    if (self.auto_subscribe and web_subscribe and 
		self.web_subscribe_requires_confirmation):
		if self.web_subscribe_requires_confirmation == 1:
		    raise mm_err.MMWebSubscribeRequiresConfirmation
		else:
		    self.AddRequest('add_member', digest, name, password)
	    elif self.auto_subscribe:
		self.ApprovedAddMember(name, password, digest)
	    else:
		self.AddRequest('add_member', digest, name, password)
	else: 
	    if not self.digestable:
		raise mm_err.MMCantDigestError
	    if self.auto_subscribe:
		self.ApprovedAddMember(name, password, digest)
	    else:
		self.AddRequest('add_member', digest, name, password)

    def ApprovedAddMember(self, name, password, digest):
	if digest:
	    self.digest_members.append(name)
	    self.digest_members.sort()
	else:
	    self.members.append(name)
	    self.members.sort()
	self.passwords[name] = password
	self.SendSubscribeAck(name, password, digest)
	self.Save()

    def DeleteMember(self, name):
	self.IsListInitialized()
# FindMatchingAddresses *should* never return more than 1 address.
# However, should log this, just to make sure.
	aliases = mm_utils.FindMatchingAddresses(name, self.members + 
						 self.digest_members)
	if not len(aliases):
	    raise mm_err.MMNoSuchUserError

	def DoActualRemoval(alias, me=self):
	    try:
		del me.passwords[alias]
	    except KeyError: 
		pass
	    try:
		me.members.remove(alias)
	    except ValueError:
		pass
	    try:
		me.digest_members.remove(alias)
	    except ValueError:
		pass

	map(DoActualRemoval, aliases)
	if self.goodbye_msg and len(self.goodbye_msg):
	    self.SendUnsubscribeAck(name)
	self.ClearBounceInfo(name)
	self.Save()

    def IsMember(self, address):
	return len(mm_utils.FindMatchingAddresses(address, self.members +
						    self.digest_members))

    def HasExplicitDest(self, msg):
	"True if list name is explicitly included among the to or cc addrs."
	# Note that host can be different!  This allows, eg, for relaying
	# from remote lists that have the same name.  Still stringent, but
	# offers a way to provide for remote exploders.
	lowname = string.lower(self.real_name)
	for recip in msg.getaddrlist('to') + msg.getaddrlist('cc'):
	    if lowname == string.lower(string.split(recip[1], '@')[0]):
		return 1
	return 0

#msg should be an IncomingMessage object.
    def Post(self, msg, approved=0):
	self.IsListInitialized()
	sender = msg.GetSender()
	# If it's the admin, which we know by the approved variable,
	# we can skip a large number of checks.
	if not approved:
	    if len(self.bad_posters):
		addrs = mm_utils.FindMatchingAddresses(sender, self.bad_posters)
		if len(addrs):
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				'Post from an untrusted email address requires '
				'moderator approval.')
	    if len(self.posters):
		addrs = mm_utils.FindMatchingAddresses(sender, self.posters)
		if not len(addrs):
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    'Only approved posters may post without '
				    'moderator approval.')
	    elif self.moderated:
		self.AddRequest('post', mm_utils.SnarfMessage(msg),
				'Moderated list: Moderator approval required.',
				# Add an extra arg to avoid generating an
				# error mail.
				1)
	    if self.member_posting_only and not self.IsMember(sender):
		self.AddRequest('post', mm_utils.SnarfMessage(msg),
				'Posters to the list must send mail from an '
				'email address on the list.')
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
				    'Too many recipients.')
 	    if (self.require_explicit_destination and
 		  not self.HasExplicitDest(msg)):
 		self.AddRequest('post', mm_utils.SnarfMessage(msg),
 				'Missing explicit list destination: '
 				'Admin approval required.')
	    if self.max_message_size > 0:
		if len(msg.body)/1024. > self.max_message_size:
		    self.AddRequest('post', mm_utils.SnarfMessage(msg),
				    'Message body too long (>%dk)' % 
				    self.max_message_size)
	if self.digestable:
	    self.SaveForDigest(msg)
	if self.archive:
	    self.ArchiveMail(msg)
	# Prepend the subject_prefix to the subject line.
	subj = msg.getheader('subject')
	prefix = self.subject_prefix
	if prefix:
	    prefix = prefix + ' '
	if not subj:
	    msg.SetHeader('Subject', '%s(no subject)' % prefix)
	else:
	    msg.SetHeader('Subject', '%s%s' % (prefix, subj))

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
	self.DeliverToList(msg, recipients, self.msg_header, self.msg_footer)
	if ack_post:
	    self.SendPostAck(msg, sender)
	self.last_post_time = time.time()
	self.post_id = self.post_id + 1
	self.Save()

    def Lock(self):
	try:
	    if self._lock_file:
		return
	except AttributeError:
	    return
	self._lock_file = posixfile.open(
	    os.path.join(mm_cfg.LOCK_DIR, '%s.lock'% self._internal_name), 'a+')
	self._lock_file.lock('w|', 1)
    
    def Unlock(self):
	self._lock_file.lock('u')
	self._lock_file.close()
	self._lock_file = None

def list_names():
    """Return the names of all lists in default list directory."""
    got = []
    for fn in os.listdir(mm_cfg.LIST_DATA_DIR):
	if not (
	    os.path.exists(
		os.path.join(os.path.join(mm_cfg.LIST_DATA_DIR, fn),
			     'config.db'))):
	    continue
	got.append(fn)
    return got
