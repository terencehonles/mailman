"Handle delivery bounce messages, doing filtering when list is set for it."

__version__ = "$Revision: 538 $"

# It's possible to get the mail-list senders address (list-admin) in the
# bounce list.   You probably don't want to have list mail sent to that
# address anyway.

import sys
import time
import regsub, string, regex, re
import mm_utils, mm_cfg, mm_err

class Bouncer:
    def InitVars(self):
	# Not configurable...
	self.bounce_info = {}

	# Configurable...
	self.bounce_processing = mm_cfg.DEFAULT_BOUNCE_PROCESSING
	self.minimum_removal_date = mm_cfg.DEFAULT_MINIMUM_REMOVAL_DATE
	self.minimum_post_count_before_bounce_action = \
		mm_cfg.DEFAULT_MINIMUM_POST_COUNT_BEFORE_BOUNCE_ACTION
	self.automatic_bounce_action = mm_cfg.DEFAULT_AUTOMATIC_BOUNCE_ACTION
	self.max_posts_between_bounces = \
		mm_cfg.DEFAULT_MAX_POSTS_BETWEEN_BOUNCES

    def GetConfigInfo(self):
	return [
            "Policies regarding systematic processing of bounce messages,"
            " to help automate recognition and handling of defunct"
            " addresses.",
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
	     0, "Action when critical or excessive bounces are detected.")
	    ]
    def ClearBounceInfo(self, email):
	email = string.lower(email)
	if self.bounce_info.has_key(email):
	    del self.bounce_info[email]

    def RegisterBounce(self, email, msg):
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
		self.HandleBouncingAddress(addr, msg)
		return
	    else:
		post_count = (self.minimum_post_count_before_bounce_action - 
			      (self.post_id - inf[1]))
		if post_count < 0:
		    post_count = 0
                remain = self.minimum_removal_date * 24 * 60 * 60 - difference
		self.LogMsg("bounce",
			    report + ("%d more allowed over %d secs"
                                      % (post_count, remain)))
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
		self.HandleBouncingAddress(addr, msg)
		return 
	    self.LogMsg("bounce",
			"digester lucked out")
	else:
	    self.LogMsg("bounce",
			"%s: address %s not a member.",
			self._internal_name,
			addr)

    def HandleBouncingAddress(self, addr, msg):
        """Disable or remove addr according to bounce_action setting."""
        if self.automatic_bounce_action == 0:
            return
        elif self.automatic_bounce_action == 1:
	    # Only send if call works ok.
            (succeeded, send) = self.DisableBouncingAddress(addr)
            did = "disabled"
        elif self.automatic_bounce_action == 2:
            (succeeded, send) = self.DisableBouncingAddress(addr)
            did = "disabled"
	    # Never send.
            send = 0
        elif self.automatic_bounce_action == 3:
            (succeeded, send) = self.RemoveBouncingAddress(addr)
	    # Always send.
            send = 1
            did = "removed"
        if send:
            if succeeded != 1:
                negative="not "
            else:
                negative=""
            recipient = self.GetAdminEmail()
            if addr in self.owner + [recipient]:
                # Whoops!  This is a bounce of a bounce notice - do not
                # perpetuate the bounce loop!  Log it prominently and be
                # satisfied with that.
                self.LogMsg("error",
                            "%s: Bounce recipient loop"
                            " encountered!\n\t%s\n\tBad admin recipient: %s",
                            self._internal_name,
                            "(Ie, bounce notification addr, itself, bounces.)",
                            addr)
                return
            import mimetools
            boundary = mimetools.choose_boundary()
            text = [""]
            text.append("(This MIME message should be"
                        " readable as plain text.)")
            text.append("")
            text.append("--" + boundary)
            text.append("Content-type: text/plain; charset=us-ascii")
            text.append("")
            text.append("This is a mailman mailing list bounce action notice:")
            text.append("")
            text.append("\tMaillist:\t%s" % self.real_name)
            text.append("\tMember:\t\t%s" % addr)
            text.append("\tAction:\t\tSubscription %s%s." % (negative, did))
            text.append("\tReason:\t\tExcessive or fatal bounces.")
            if succeeded != 1:
                text.append("\tBUT:\t\t%s\n" % succeeded)
            text.append("")
            if did == "disabled" and succeeded == 1:
                text.append("You can reenable their subscription by visiting "
                            "their options page")
                text.append("(via %s) and using your"
                            % self.GetScriptURL('listinfo'))
                text.append(
                    "list admin password to authorize the option change.")
            text.append("")
            text.append("The triggering bounce notice is attached below.")
            text.append("")
            text.append("Questions?  Contact the mailman site admin,")
            text.append("\t" + mm_cfg.MAILMAN_OWNER)

            text.append("")
            text.append("--" + boundary)
            text.append("Content-type: text/plain; charset=us-ascii")
            text.append("")
            text.append(string.join(msg.headers, ''))
            text.append("")
            text.append(mm_utils.QuotePeriods(msg.body))
            text.append("")
            text.append("--" + boundary + "--")

            if negative:
                negative = string.upper(negative)
            self.SendTextToUser(subject = ("%s member %s %s%s due to bounces"
                                           % (self.real_name, addr,
                                              negative, did)),
                                recipient = recipient,
                                sender = mm_cfg.MAILMAN_OWNER,
                                add_headers = [
                                    "Errors-To: %s" % mm_cfg.MAILMAN_OWNER,
                                    "MIME-version: 1.0",
                                    "Content-type: multipart/mixed;"
                                    ' boundary="%s"' % boundary],
                                text = string.join(text, '\n'))
    def DisableBouncingAddress(self, addr):
	"""Disable delivery for bouncing user address.

	Returning success and notification status."""
        if not self.IsMember(addr):
            reason = "User not found."
	    self.LogMsg("bounce", "%s: NOT disabled %s: %s",
                        self.real_name, addr, reason)
            return reason, 1
	try:
	    if self.GetUserOption(addr, mm_cfg.DisableDelivery):
		# No need to send out notification if they're already disabled.
		self.LogMsg("bounce",
			    "%s: already disabled %s", self.real_name, addr)
		return 1, 0
	    else:
		self.SetUserOption(addr, mm_cfg.DisableDelivery, 1)
		self.LogMsg("bounce",
			    "%s: disabled %s", self.real_name, addr)
		self.Save()
		return 1, 1
	except mm_err.MMNoSuchUserError:
	    self.LogMsg("bounce", "%s: NOT disabled %s: %s",
                        self.real_name, addr, mm_err.MMNoSuchUserError)
	    self.ClearBounceInfo(addr)
            self.Save()
            return mm_err.MMNoSuchUserError, 1
	    
    def RemoveBouncingAddress(self, addr):
	"""Unsubscribe user with bouncing address.

	Returning success and notification status."""
        if not self.IsMember(addr):
            reason = "User not found."
	    self.LogMsg("bounce", "%s: NOT removed %s: %s",
                        self.real_name, addr, reason)
            return reason, 1
	try:
	    self.DeleteMember(addr, "bouncing addr")
	    self.LogMsg("bounce", "%s: removed %s", self.real_name, addr) 
            self.Save()
            return 1, 1
	except mm_err.MMNoSuchUserError:
	    self.LogMsg("bounce", "%s: NOT removed %s: %s",
                        self.real_name, addr, mm_err.MMNoSuchUserError)
	    self.ClearBounceInfo(addr)
            self.Save()
            return mm_err.MMNoSuchUserError, 1

    # Return 0 if we couldn't make any sense of it, 1 if we handled it.
    def ScanMessage(self, msg):
##	realname, who_from = msg.getaddr('from')
##	who_info = string.lower(who_from)
        candidates = []
	who_info = string.lower(msg.GetSender())
        at_index = string.find(who_info, '@')
	if at_index != -1:
	    who_from = who_info[:at_index]
	    remote_host = who_info[at_index+1:]
	else:
	    who_from = who_info
	    remote_host = self.host_name
	if not who_from in ['mailer-daemon', 'postmaster', 'orphanage',
			    'postoffice', 'ucx_smtp', 'a2']:
	    return 0
	mime_info = msg.getheader('content-type')
	boundry = None
	if mime_info:
	    mime_info_parts = regsub.splitx(
                mime_info, '[Bb][Oo][Uu][Nn][Dd][Aa][Rr][Yy]="[^"]+"')
	    if len(mime_info_parts) > 1:
		boundry = regsub.splitx(mime_info_parts[1],
                                        '"[^"]+"')[1][1:-1]

	if boundry:
	    relevant_text = string.split(msg.body, '--%s' % boundry)[1]
	else:
	    # This looks strange, but at least 2 are going to be no-ops.
	    relevant_text = regsub.split(msg.body,
                                         '^.*Message header follows.*$')[0]
	    relevant_text = regsub.split(relevant_text,
                                         '^The text you sent follows:.*$')[0]
	    relevant_text = regsub.split(
                relevant_text, '^Additional Message Information:.*$')[0]
	    relevant_text = regsub.split(relevant_text,
                                         '^-+Your original message-+.*$')[0]
	
	BOUNCE = 1
	REMOVE = 2

	# Bounce patterns where it's simple to figure out the email addr.
	email_regexp = '<?\([^ \t@s|<>]+@[^ \t@<>]+\.[^ \t<>.]+\)>?'
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
	# patterns we can't directly extract the email (special case these)
	messy_pattern_1 = regex.compile('^Recipient .*$')
	messy_pattern_2 = regex.compile('^Addressee: .*$')
	messy_pattern_3 = regex.compile('^User .* not listed.*$')
	messy_pattern_4 = regex.compile('^550 [^ ]+\.\.\. User unknown.*$')
	messy_pattern_5 = regex.compile('^User [^ ]+ is not defined.*$')
	messy_pattern_6 = regex.compile('^[ \t]*[^ ]+: User unknown.*$')
	messy_pattern_7 = regex.compile('^[^ ]+ - User currently disabled.*$')

        # Patterns that don't have the email
	separate_cue_1 = re.compile(
            '^554 [^ ]+\.\.\. unknown mailer error.*$', re.I)
        separate_addr_1 = regex.compile('expanded from: %s' % email_regexp)

	message_grokked = 0
        use_prospects = 0
        prospects = []                  # If bad but no candidates found.

	for line in string.split(relevant_text, '\n'):
	    for pattern, action in simple_bounce_pats:
		if pattern.match(line) <> -1:
		    email = self.ExtractBouncingAddr(line)
		    if action == REMOVE:
			candidates = candidates + string.split(email,',')
			message_grokked = 1
			continue
		    elif action == BOUNCE:
			emails = string.split(email,',')
			for email_addr in emails:
			    self.RegisterBounce(email_addr, msg)
			message_grokked = 1
			continue
		    else:
			message_grokked = 1
			continue

	    # Now for the special case messages that are harder to parse...
	    if (messy_pattern_1.match(line) <> -1
                or messy_pattern_2.match(line) <> -1):
		username = string.split(line)[1]
		self.RegisterBounce('%s@%s' % (username, remote_host), msg)
		message_grokked = 1
		continue
	    if (messy_pattern_3.match(line) <> -1
                or messy_pattern_4.match(line) <> -1
                or messy_pattern_5.match(line) <> -1):
		username = string.split(line)[1]
                candidates.append('%s@%s' % (username, remote_host))
		message_grokked = 1
		continue
	    if messy_pattern_6.match(line) <> -1:
		username = string.split(string.strip(line))[0][:-1]
                candidates.append('%s@%s' % (username, remote_host))
		message_grokked = 1
		continue
	    if messy_pattern_7.match(line) <> -1:
		username = string.split(string.strip(line))[0]
                candidates.append('%s@%s' % (username, remote_host))
		message_grokked = 1
		continue

            if separate_cue_1.match(line):
                # Here's an error message that doesn't contain the addr.
                # Set a flag to use prospects found on separate lines.
                use_prospects = 1
            if separate_addr_1.search(line) != -1:
                # Found an addr that *might* be part of an error message.
                # Register it on prospects, where it will only be used if a 
                # separate check identifies this message as an error message.
                prospects.append(separate_addr_1.group(1))

        if use_prospects and prospects:
            candidates = prospects

        did = []
        for i in candidates:
	    el = string.find(i, "...")
	    if el != -1:
		i = i[:el]
	    if len(i) > 1 and i[0] == '<':
		# Use stuff after open angle and before (optional) close:
		i = regsub.splitx(i[1:], ">")[0]
            if i not in did:
                self.HandleBouncingAddress(i, msg)
                did.append(i)
	return message_grokked

    def ExtractBouncingAddr(self, line):
	email = regsub.splitx(line, '[^ \t@<>]+@[^ \t@<>]+\.[^ \t<>.]+')[1]
	if email[0] == '<':
	    return regsub.splitx(email[1:], ">")[0]
	else:
	    return email
