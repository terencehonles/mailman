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


"Handle delivery bounce messages, doing filtering when list is set for it."


# It's possible to get the mail-list senders address (list-admin) in the
# bounce list.   You probably don't want to have list mail sent to that
# address anyway.

import sys
import time
import regsub, string, regex, re
import Utils
import mm_cfg
import Errors

class Bouncer:
    def InitVars(self):
	# Not configurable...

        # self.bounce_info registers observed bounce incidents.  It's a
        # dict mapping members addrs to a list:
        #  [
        #    time.time() of last bounce,
        #    post_id of first offending bounce in current sequence,
        #    post_id of last offending bounce in current sequence
        #  ]
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
        """Detect and handle repeat-offender bounce addresses.
        
        We use very sketchy bounce history profiles in self.bounce_info
        (see comment above it's initialization), together with list-
        specific thresholds self.minimum_post_count_before_bounce_action
        and self.max_posts_between_bounces."""

        # Set 'dirty' if anything needs to be save in the finally clause.
        dirty = 0
        report = "%s: %s - " % (self.real_name, email)

        try:

            now = time.time()
            secs_per_day = 24 * 60 * 60

            # Take the opportunity to cull expired entries.
            pid = self.post_id
            maxposts = self.max_posts_between_bounces
            stalesecs = self.minimum_removal_date * secs_per_day * 5
            for k, v in self.bounce_info.items():
                if now - v[0] > stalesecs:
                    # It's been long enough to drop their bounce record:
                    del self.bounce_info[k]
                    dirty = 1

            this_dude = Utils.FindMatchingAddresses(email,
                                                    self.bounce_info)
            if not this_dude:
                # No (or expired) priors - new record.
                self.bounce_info[string.lower(email)] = [now, self.post_id,
                                                         self.post_id]
                self.LogMsg("bounce", report + "first")
                dirty = 1
                return

            # There are some priors.
            addr = string.lower(this_dude[0])
            hist = self.bounce_info[addr]
            difference = now - hist[0]
            if len(Utils.FindMatchingAddresses(addr, self.members)):
                if self.post_id - hist[2] > self.max_posts_between_bounces:
                    # There's been enough posts since last bounce that we're
                    # restarting.  (Might should keep track of who goes stale
                    # how often.)
                    self.LogMsg("bounce", report + "first fresh")
                    self.bounce_info[addr] = [now, self.post_id, self.post_id]
                    dirty = 1
                    return
                self.bounce_info[addr][2] = self.post_id
                dirty = 1
                if ((self.post_id - hist[1] >
                     self.minimum_post_count_before_bounce_action)
                    and
                    (difference > self.minimum_removal_date * secs_per_day)):
                    self.LogMsg("bounce", report + "exceeded limits")
                    self.HandleBouncingAddress(addr, msg)
                    return
                else:
                    post_count = (self.minimum_post_count_before_bounce_action
                                  - (self.post_id - hist[1]))
                    if post_count < 0:
                        post_count = 0
                    remain = (self.minimum_removal_date
                              * secs_per_day - difference)
                    self.LogMsg("bounce",
                                report + ("%d more allowed over %d secs"
                                          % (post_count, remain)))
                    return

            elif len(Utils.FindMatchingAddresses(addr, self.digest_members)):
                if self.volume > hist[1]:
                    self.LogMsg("bounce",
                                "%s: first fresh (D)", self._internal_name)
                    self.bounce_info[addr] = [now, self.volume, self.volume]
                    return
                if difference > self.minimum_removal_date * secs_per_day:
                    self.LogMsg("bounce", report + "exceeded limits (D)")
                    self.HandleBouncingAddress(addr, msg)
                    return 
                self.LogMsg("bounce", report + "digester lucked out")
            else:
                self.LogMsg("bounce",
                            "%s: address %s not a member.",
                            self._internal_name,
                            addr)
        finally:
            if dirty:
                self.Save()

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
            # report about success
            but = ''
            if succeeded <> 1:
                but = 'BUT:        %s' % succeeded
            # disabled?
            if did == 'disabled' and succeeded == 1:
                reenable = Utils.maketext(
                    'reenable.txt',
                    {'admin_url': self.GetAbsoluteScriptURL('admin'),
                     })
            else:
                reenable = ''
            # the mail message text
            text = Utils.maketext(
                'bounce.txt',
                {'boundary' : boundary,
                 'listname' : self.real_name,
                 'addr'     : addr,
                 'negative' : negative,
                 'did'      : did,
                 'but'      : but,
                 'reenable' : reenable,
                 'owneraddr': mm_cfg.MAILMAN_OWNER,
                 })
            # add this here so it doesn't get wrapped/filled
            text = text + '\n\n--' + boundary + \
                   '\nContent-type: text/plain; charset=us-ascii\n'

            # we do this here so this text won't be wrapped.  note that
            # 'bounce.txt' has a trailing newline
            text = text + \
                   string.join(msg.headers, '') + '\n' + \
                   Utils.QuotePeriods(msg.body) + '\n' + \
                   '--' + boundary + '--'

            if negative:
                negative = string.upper(negative)

            self.SendTextToUser(
                subject = "%s member %s bouncing - %s%s"
                % (self.real_name, addr, negative, did),
                recipient = recipient,
                sender = mm_cfg.MAILMAN_OWNER,
                add_headers = [
                    "Errors-To: %s" % mm_cfg.MAILMAN_OWNER,
                    "MIME-version: 1.0",
                    "Content-type: multipart/mixed;"
                    ' boundary="%s"' % boundary],
                text = text)

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
	except Errors.MMNoSuchUserError:
	    self.LogMsg("bounce", "%s: NOT disabled %s: %s",
                        self.real_name, addr, Errors.MMNoSuchUserError)
	    self.ClearBounceInfo(addr)
            self.Save()
            return Errors.MMNoSuchUserError, 1
	    
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
	except Errors.MMNoSuchUserError:
	    self.LogMsg("bounce", "%s: NOT removed %s: %s",
                        self.real_name, addr, Errors.MMNoSuchUserError)
	    self.ClearBounceInfo(addr)
            self.Save()
            return Errors.MMNoSuchUserError, 1

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
	    relevant_text = string.split(msg.body, '--%s' % boundry)
            # Invalid MIME messages shouldn't cause exceptions
            if len(relevant_text) >= 2:
                relevant_text = relevant_text[1]
            else:
                relevant_text = relevant_text[0]
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
	email_regexp = '<?\([^ \t@|<>]+@[^ \t@<>]+\.[^ \t<>.]+\)>?'
	simple_bounce_pats = (
	    (regex.compile('.*451 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*554 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*552 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*501 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*553 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('.*550 %s.*' % email_regexp), BOUNCE),
	    (regex.compile('%s .bounced.*' % email_regexp), BOUNCE),
	    (regex.compile('.*%s\.\.\. Deferred.*' % email_regexp), BOUNCE),
	    (regex.compile('.*User %s not known.*' % email_regexp), REMOVE),
	    (regex.compile('.*%s: User unknown.*' % email_regexp), REMOVE),
            (regex.compile('.*%s\.\.\. User unknown' % email_regexp), REMOVE))
	# patterns we can't directly extract the email (special case these)
	messy_pattern_1 = regex.compile('^Recipient .*$')
	messy_pattern_2 = regex.compile('^Addressee: .*$')
	messy_pattern_3 = regex.compile('^User .* not listed.*$')
	messy_pattern_4 = regex.compile('^550 [^ ]+\.\.\. User unknown.*$')
	messy_pattern_5 = regex.compile('^User [^ ]+ is not defined.*$')
	messy_pattern_6 = regex.compile('^[ \t]*[^ ]+: User unknown.*$')
	messy_pattern_7 = regex.compile('^[^ ]+ - User currently disabled.*$')

        # Patterns for cases where email addr is separate from error cue.
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
		    candidates.append((string.split(email,',')[0], action))
		    message_grokked = 1

	    # Now for the special case messages that are harder to parse...
	    if (messy_pattern_1.match(line) <> -1
                or messy_pattern_2.match(line) <> -1):
		username = string.split(line)[1]
		candidates.append(('%s@%s' % (username, remote_host),
				   BOUNCE))
		message_grokked = 1
		continue
	    if (messy_pattern_3.match(line) <> -1
                or messy_pattern_4.match(line) <> -1
                or messy_pattern_5.match(line) <> -1):
		username = string.split(line)[1]
		candidates.append(('%s@%s' % (username, remote_host),
				   REMOVE))
		message_grokked = 1
		continue
	    if messy_pattern_6.match(line) <> -1:
		username = string.split(string.strip(line))[0][:-1]
		candidates.append(('%s@%s' % (username, remote_host),
				   REMOVE))
		message_grokked = 1
		continue
	    if messy_pattern_7.match(line) <> -1:
		username = string.split(string.strip(line))[0]
		candidates.append(('%s@%s' % (username, remote_host),
				   REMOVE))
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
                prospects.append((separate_addr_1.group(1), BOUNCE))

        if use_prospects and prospects:
            candidates = candidates + prospects

        did = []
        for who, action in candidates:
	    # First clean up some cruft around the addrs.
	    el = string.find(who, "...")
	    if el != -1:
		who = who[:el]
	    if len(who) > 1 and who[0] == '<':
		# Use stuff after open angle and before (optional) close:
		who = regsub.splitx(who[1:], ">")[0]
            if who not in did:
		if action == REMOVE:
		    self.HandleBouncingAddress(who, msg)
		else:
		    self.RegisterBounce(who, msg)
                did.append(who)
	return message_grokked

    def ExtractBouncingAddr(self, line):
	email = regsub.splitx(line, '[^ \t@<>]+@[^ \t@<>]+\.[^ \t<>.]+')[1]
	if email[0] == '<':
	    return regsub.splitx(email[1:], ">")[0]
	else:
	    return email
