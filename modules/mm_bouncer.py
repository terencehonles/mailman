# It's possible to get the mail-list senders address (list-admin) in the bounce list.  
# You probably don't want to have list mail sent to that address anyway.

import sys
import time
import regsub, string, regex
import mm_utils, mm_cfg, mm_err

class Bouncer:
    def InitVars(self):
	# Not configurable...
	self.bounce_info = {}

	
	self.bounce_processing = mm_cfg.DEFAULT_BOUNCE_PROCESSING
	# Configurable...
	self.minimum_removal_date = mm_cfg.DEFAULT_MINIMUM_REMOVAL_DATE
	self.minimum_post_count_before_bounce_action = \
		mm_cfg.DEFAULT_MINIMUM_POST_COUNT_BEFORE_BOUNCE_ACTION
	self.automatic_bounce_action = \
                                     mm_cfg.DEFAULT_AUTOMATIC_BOUNCE_ACTION
	self.max_posts_between_bounces = \
		mm_cfg.DEFAULT_MAX_POSTS_BETWEEN_BOUNCES

    def GetConfigInfo(self):
	return [
	    ('bounce_processing', mm_cfg.Toggle, ('No', 'Yes'), 0,
	     'Try to figure out error messages automatically? '),
	    ('minimum_removal_date', mm_cfg.Number, 3, 0,
	     'Minimum number of days an address has been non-fatally '
             'bad before we take action'),
	    ('minimum_post_count_before_bounce_action', mm_cfg.Number, 3, 0,
	     'Minimum number of posts to the list since members first '
             'bounce before we consider removing them from the list'),
	    ('max_posts_between_bounces', mm_cfg.Number, 3, 0,
	     "Maximum number of messages your list gets in an hour.  "
             "(Yes, bounce detection finds this info useful)"),
	    ('automatic_bounce_action', mm_cfg.Radio,
	     ("Do nothing",
              "Disable and notify me",
              "Disable and DON'T notify me",
	      "Remove and notify me"),
	     0, "Action when fatal or excessive bounces are detected.")
	    ]
    def ClearBounceInfo(self, email):
	email = string.lower(email)
	if self.bounce_info.has_key(email):
	    del self.bounce_info[email]

    def RegisterBounce(self, email):
	report = "%s: %s - " % (self.real_name, email)
	bouncees = self.bounce_info.keys()
	this_dude = mm_utils.FindMatchingAddresses(email, bouncees)
	now = time.time()
	if not len(this_dude):
	    # Time address went bad, post where address went bad,
	    # What the last post ID was that we saw a bounce.
	    self.bounce_info[string.lower(email)] = [now, self.post_id,
						     self.post_id]
	    self.LogMsg("bounce", report + "first")
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
		self.LogMsg("bounce",
			    report + "first fresh")
		self.bounce_info[addr] = [now, self.post_id, self.post_id]
		return
	    self.bounce_info[addr][2] = self.post_id
	    if ((self.post_id - inf[1] >
                 self.minimum_post_count_before_bounce_action)
		and difference > self.minimum_removal_date * 24 * 60 * 60):
		self.LogMsg("bounce", report + "exceeded limits")
		self.HandleBouncingAddress(addr)
		return
	    else:
		post_count = (self.minimum_post_count_before_bounce_action - 
			      self.post_id - inf[1])
		if post_count < 0:
		    post_count = 0
		self.LogMsg("bounce",
			    (report + ("%d more posts, %d more secs"
				       (post_count,
					(self.minimum_removal_date
					 * 24 * 60 * 60 - difference)))))
		self.Save()
		return

	elif len(mm_utils.FindMatchingAddresses(addr, self.digest_members)):
	    if self.volume > inf[1]:
		self.LogMsg("bounce",
			    "%s: first fresh (D)",
			    self._internal_name)
		self.bounce_info[addr] = [now, self.volume, self.volume]
		return
	    if difference > self.minimum_removal_date * 24 * 60 * 60:
		self.LogMsg("bounce", "exceeded limits (D)")
		self.HandleBouncingAddress(addr)
		return 
	    self.LogMsg("bounce",
			"digester lucked out")
	else:
	    self.LogMsg("bounce",
			"%s: address %s not a member.",
			self._internal_name,
			addr)

    def HandleBouncingAddress(self, addr):
        """Disable or remove addr according to bounce_action setting."""
        if self.automatic_bounce_action == 0:
            return
        elif self.automatic_bounce_action == 1:
            succeeded = self.DisableBouncingAddress(addr)
            did = "disabled"
            send = 1
        elif self.automatic_bounce_action == 2:
            succeeded = self.DisableBouncingAddress(addr)
            did = "disabled"
            send = 0
        elif self.automatic_bounce_action == 3:
            succeeded = self.RemoveBouncingAddress(addr)
            did = "removed"
            send = 1
        if send:
            if succeeded != 1:
                negative="not "
                recipient = mm_cfg.MAILMAN_OWNER
            else:
                negative=""
                recipient = self.GetAdminEmail()
            text = ("This is a mailman maillist administrator notice.\n"
                    "\n\tMaillist:\t%s\n"
                    "\tMember:\t\t%s\n"
                    "\tAction:\t\tSubscription %s%s.\n"
                    "\tReason:\t\tExcessive or fatal bounces.\n"
                    % (self.real_name, addr, negative, did))
            if succeeded != 1:
                text = text + "\tFailure reason:\t%s\n\n" % succeeded
            else:
                text = text + "\n"
            if did == "disabled" and succeeded == 1:
                text = text + (
                    "You can reenable their subscription by visiting "
                    "their options page\n"
                    "(via %s) and using your\n"
                    "list admin password to authorize the option change.\n\n"
                    % self.GetScriptURL('listinfo'))
            text = text + ("Questions?  Contact the mailman site admin,\n%s"
                           % mm_cfg.MAILMAN_OWNER)
            if negative:
                negative = string.upper(negative)
            self.SendTextToUser(subject = ("%s member %s %s%s due to bounces"
                                           % (self.real_name, addr,
                                              negative, did)),
                                recipient = recipient,
                                sender = mm_cfg.MAILMAN_OWNER,
                                errorsto = mm_cfg.MAILMAN_OWNER,
                                text = text)
    def DisableBouncingAddress(self, addr):
        if not self.IsMember(addr):
            reason = "User not found."
	    self.LogMsg("bounce", "%s: NOT disabled %s: %s",
                        self.real_name, addr, reason)
            return reason
	try:
	    self.SetUserOption(addr, mm_cfg.DisableDelivery, 1)
	    self.LogMsg("bounce", "%s: disabled %s", self.real_name, addr)
            self.Save()
            return 1
	except mm_err.MMNoSuchUserError:
	    self.LogMsg("bounce", "%s: NOT disabled %s: %s",
                        self.real_name, addr, mm_err.MMNoSuchUserError)
	    self.ClearBounceInfo(addr)
            self.Save()
            return mm_err.MMNoSuchUserError
	    
    def RemoveBouncingAddress(self, addr):
        if not self.IsMember(addr):
            reason = "User not found."
	    self.LogMsg("bounce", "%s: NOT removed %s: %s",
                        self.real_name, addr, reason)
            return reason
	try:
	    self.DeleteMember(addr)
	    self.LogMsg("bounce", "%s: removed %s", self.real_name, addr) 
            self.Save()
            return 1
	except mm_err.MMNoSuchUserError:
	    self.LogMsg("bounce", "%s: NOT removed %s: %s",
                        self.real_name, addr, mm_err.MMNoSuchUserError)
	    self.ClearBounceInfo(addr)
            self.Save()
            return mm_err.MMNoSuchUserError

    # Return 0 if we couldn't make any sense of it, 1 if we handled it.
    def ScanMessage(self, msg):
##	realname, who_from = msg.getaddr('from')
##	who_info = string.lower(who_from)
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

	did = []
	for line in string.split(relevent_text, '\n'):
	    for pattern, action in simple_bounce_pats:
		if pattern.match(line) <> -1:
		    email = self.ExtractBouncingAddr(line)
		    if action == REMOVE:
			emails = string.split(email,',')
			for email_addr in emails:
			    if email_addr not in did:
				self.HandleBouncingAddress(
				    string.strip(email_addr))
				did.append(email_addr)
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
		self.HandleBouncingAddress('%s@%s' % (username, remote_host))
		message_groked = 1
		continue
	    if messy_pattern_6.match(line) <> -1:
		username = string.split(string.strip(line))[0][:-1]
		self.HandleBouncingAddress('%s@%s' % (username, remote_host))
		message_groked = 1
		continue
	    if messy_pattern_7.match(line) <> -1:
		username = string.split(string.strip(line))[0]
		self.HandleBouncingAddress('%s@%s' % (username, remote_host))
		message_groked = 1
		continue

	return message_groked

    def ExtractBouncingAddr(self, line):
	# First try with angles:
	email = regsub.splitx(line, '[^ \t@<>]+@[^ \t@<>]+\.[^ \t<>.]+')[1]
	if email[0] == '<':
	    return email[1:-1]
	else:
	    return email
