# It's possible to get the mail-list senders address (list-admin) in the bounce list.  
# You probably don't want to have list mail sent to that address anyway.

import sys
import time
import regsub, string, regex
import mm_utils, mm_cfg

my_log = open('/tmp/bounce.log', 'a+')
class Bouncer:
    def InitVars(self):
	# Not configurable...
	self.bounce_info = {}

	
	self.bounce_processing = mm_cfg.DEFAULT_BOUNCE_PROCESSING
	# Configurable...
	self.minimum_removal_date = mm_cfg.DEFAULT_MINIMUM_REMOVAL_DATE
	self.minimum_post_count_before_removal = \
		mm_cfg.DEFAULT_MINIMUM_POST_COUNT_BEFORE_REMOVAL
	self.automatically_remove = mm_cfg.DEFAULT_AUTOMATICALLY_REMOVE
	self.max_posts_between_bounces = \
		mm_cfg.DEFAULT_MAX_POSTS_BETWEEN_BOUNCES

    def GetConfigInfo(self):
	return [
	    ('bounce_processing', mm_cfg.Toggle, ('No', 'Yes'), 0,
	     'Try to figure out error messages automatically? '),
	    ('minimum_removal_date', mm_cfg.Number, 3, 0,
	     'Minimum number of days an address has been bad before we consider nuking it'),
	    ('minimum_post_count_before_removal', mm_cfg.Number, 3, 0,
	     'Minimum number of posts to the list since your first bounce before we consider '
	     'removing you from the list'),
	    ('max_posts_between_bounces', mm_cfg.Number, 3, 0,
	     "Maximum number of messages your list gets in an hour.  (Yes, bounce detection "
	     "finds this info useful)"),
	    ('automatically_remove', mm_cfg.Radio, ("Don't remove; Notify me", "Remove, but "
						    "notify me", "Remove and don't notify me"),
	     0, "Automatically remove addresses considered for removal, or alert you?")
	    ]
    def ClearBounceInfo(self, email):
	my_log.write("*Removed %s from %s (%s)\n" % (email, self.real_name, time.ctime(time.time())))
	email = string.lower(email)
	if self.bounce_info.has_key(email):
	    del self.bounce_info[email]

    def RegisterBounce(self, email):
	my_log.write("Bouncing %s on list %s (%s) -- " % (email, self.real_name, time.ctime(time.time())))
	bouncees = self.bounce_info.keys()
	this_dude = mm_utils.FindMatchingAddresses(email, bouncees)
	now = time.time()
	if not len(this_dude):
	    # Time address went bad, post where address went bad,
	    # What the last post ID was that we saw a bounce.
	    self.bounce_info[string.lower(email)] = [now, self.post_id,
						     self.post_id]
	    my_log.write("First bounce\n")
	    self.Save()
	    return

	addr = string.lower(this_dude[0])
	inf = self.bounce_info[addr]
	difference = now - inf[0]
	if len(mm_utils.FindMatchingAddresses(addr, self.members)):
	    if self.post_id - inf[2] > self.max_posts_between_bounces:
		# Stale entry that's now being restarted...
		# Should maybe keep track in see if people become stale entries
		# often...
		my_log.write("First fresh bounce on a stale addr.\n")
		self.bounce_info[addr] = [now, self.post_id, self.post_id]
		return
	    self.bounce_info[addr][2] = self.post_id
	    if (self.post_id - inf[1] > self.minimum_post_count_before_removal
		and difference > self.minimum_removal_date * 24 * 60 * 60):
		my_log.write("You're out of here...\n")
		self.RemoveBouncingAddress(addr)
		return
	    else:
		post_count = (self.minimum_post_count_before_removal - 
			      self.post_id - inf[1])
		if post_count < 0:
		    post_count = 0
		my_log.write("%d more posts, %d more secs\n" % 
			     (post_count,
			      self.minimum_removal_date * 24 * 60 * 60 -
			      difference))
		self.Save()
		return

	elif len(mm_utils.FindMatchingAddresses(addr, self.digest_members)):
	    if self.volume > inf[1]:
		my_log.write("First fresh bounce on a stale addr (D).\n")
		self.bounce_info[addr] = [now, self.volume, self.volume]
		return
	    if difference > self.minimum_removal_date * 24 * 60 * 60:
		my_log.write("Seeya, digest-ee...\n")
		self.RemoveBouncingAddress(addr)
		return 
	    my_log.write("digester lucked out, he's still got time!\n")
	else:
	    my_log.write("Address %s wasn't a member of the list.\n" % addr)

	    
    def RemoveBouncingAddress(self, addr):
	try:
	    self.DeleteMember(addr)
	    # Send mail to the user...
	except:
	    self.ClearBounceInfo(addr)
	self.Save()

    # Return 0 if we couldn't make any sense of it, 1 if we handled it.
    def ScanMessage(self, msg):
#	realname, who_from = msg.getaddr('from')
#	who_info = string.lower(who_from)
	who_info = string.lower(msg.GetSender())
        at_index = string.find(who_info, '@')
	who_from = who_info[:at_index]
	remote_host = who_info[at_index+1:]
	if not who_from in ['mailer-daemon', 'postmaster', 'orphanage',
			    'postoffice', 'ucx_smtp', 'a2']:
	    return 0
	mime_info = msg.getheader('content-type')
	boundry = None
	if mime_info:
	    mime_info_parts = regsub.splitx(mime_info, '[Bb][Oo][Uu][Nn][Dd][Aa][Rr][Yy]="[^"]+"')
	    if len(mime_info_parts) > 1:
		boundry = regsub.splitx(mime_info_parts[1], '"[^"]+"')[1][1:-1]

	if boundry:
	    relevent_text = string.split(msg.body, '--%s' % boundry)[1]
	else:
	    # This looks strange, but at least 2 of these are going to be no-ops.
	    relevent_text = regsub.split(msg.body, '^.*Message header follows.*$')[0]
	    relevent_text = regsub.split(relevent_text, '^The text you sent follows:.*$')[0]
	    relevent_text = regsub.split(relevent_text, '^Additional Message Information:.*$')[0]
	    relevent_text = regsub.split(relevent_text, '^-+Your original message-+.*$')[0]
	
	BOUNCE = 1
	REMOVE = 2

	# Bounce patterns where it's simple to figure out the email addr.
	email_regexp = '<?[^ \t@<>]+@[^ \t@<>]+\.[^ \t<>.]+>?'
	simple_bounce_pats = (
	    (regex.compile('.*451 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*554 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*552 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*501 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*553 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*550 %s.*' % email_regexp), REMOVE),
	    (regex.compile('%s .bounced.*' % email_regexp), BOUNCE),
	    (regex.compile('.*%s\.\.\. Deferred.*' % email_regexp), BOUNCE),
	    (regex.compile('.*User %s not known.*' % email_regexp), REMOVE),
	    (regex.compile('.*%s: User unknown.*' % email_regexp), REMOVE))
	# patterns that we can't directly extract the email (special case these)
	messy_pattern_1 = regex.compile('^Recipient .*$')
	messy_pattern_2 = regex.compile('^Addressee: .*$')
	messy_pattern_3 = regex.compile('^User .* not listed.*$')
	messy_pattern_4 = regex.compile('^550 [^ ]+\.\.\. User unknown.*$')
	messy_pattern_5 = regex.compile('^User [^ ]+ is not defined.*$')
	messy_pattern_6 = regex.compile('^[ \t]*[^ ]+: User unknown.*$')
	messy_pattern_7 = regex.compile('^[^ ]+ - User currently disabled.*$')

	message_groked = 0

	for line in string.split(relevent_text, '\n'):
	    for pattern, action in simple_bounce_pats:
		if pattern.match(line) <> -1:
		    email = self.ExtractBouncingAddr(line)
		    if action == REMOVE:
			emails = string.split(email,',')
			for email_addr in emails:
			    self.RemoveBouncingAddress(string.strip(email_addr))
			message_groked = 1
			continue
		    elif action == BOUNCE:
			emails = string.split(email,',')
			for email_addr in emails:
			    self.RegisterBounce(email_addr)
			message_groked = 1
			continue
		    else:
			message_groked = 1
			continue

	    # Now for the special case messages that are harder to parse...
	    if messy_pattern_1.match(line) <> -1 or messy_pattern_2.match(line) <> -1:
		username = string.split(line)[1]
		self.RegisterBounce('%s@%s' % (username, remote_host))
		message_groked = 1
		continue
	    if messy_pattern_3.match(line) <> -1 or messy_pattern_4.match(line) <> -1 or messy_pattern_5.match(line) <> -1:
		username = string.split(line)[1]
		self.RemoveBouncingAddress('%s@%s' % (username, remote_host))
		message_groked = 1
		continue
	    if messy_pattern_6.match(line) <> -1:
		username = string.split(string.strip(line))[0][:-1]
		self.RemoveBouncingAddress('%s@%s' % (username, remote_host))
		message_groked = 1
		continue
	    if messy_pattern_7.match(line) <> -1:
		username = string.split(string.strip(line))[0]
		self.RemoveBouncingAddress('%s@%s' % (username, remote_host))
		message_groked = 1
		continue

	return message_groked

    def ExtractBouncingAddr(self, line):
	email = regsub.splitx(line, '<?[^ \t@<>]+@[^ \t@<>]+\.[^ \t<>.]+>?')[1]
	if email[0] == '<':
	    return email[1:-1]
	else:
	    return email
