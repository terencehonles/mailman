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


"Handle delivery bounce messages, doing filtering when list is set for it."


# It's possible to get the mail-list senders address (list-admin) in the
# bounce list.   You probably don't want to have list mail sent to that
# address anyway.

import sys
import time

from Mailman import mm_cfg
from Mailman import Errors
from Mailman import Utils
from Mailman import Message
from Mailman.Logging.Syslog import syslog
from Mailman.i18n import _

EMPTYSTRING = ''



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
            _('''Policies regarding systematic processing of bounce messages,
            to help automate recognition and handling of defunct
            addresses.'''),
            
            ('bounce_processing', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('Try to figure out error messages automatically?')),

            ('minimum_removal_date', mm_cfg.Number, 3, 0,
             _('''Minimum number of days an address has been non-fatally bad
             before we take action''')),

            ('minimum_post_count_before_bounce_action', mm_cfg.Number, 3, 0,
             _('''Minimum number of posts to the list since members first
             bounce before we consider removing them from the list''')),

            ('max_posts_between_bounces', mm_cfg.Number, 3, 0,
             _('''Maximum number of messages your list gets in an hour. (Yes,
             bounce detection finds this info useful)''')),

            ('automatic_bounce_action', mm_cfg.Radio,
             (_("Do nothing"),
              _("Disable and notify me"),
              _("Disable and DON'T notify me"),
              _("Remove and notify me")),
             0,
             _("Action when critical or excessive bounces are detected."))
            ]

    def ClearBounceInfo(self, email):
        email = email.lower()
        if self.bounce_info.has_key(email):
            del self.bounce_info[email]

    def RegisterBounce(self, email, msg):
        """Detect and handle repeat-offender bounce addresses.
        
        We use very sketchy bounce history profiles in self.bounce_info
        (see comment above it's initialization), together with list-
        specific thresholds self.minimum_post_count_before_bounce_action
        and self.max_posts_between_bounces.
        """

        # Set 'dirty' if anything needs to be save in the finally clause.
        report = "%s: %s - " % (self.real_name, email)
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

        this_dude = Utils.FindMatchingAddresses(email, self.bounce_info)
        if not this_dude:
            # No (or expired) priors - new record.
            self.bounce_info[email.lower()] = [now, self.post_id,
                                               self.post_id]
            syslog("bounce", report + "first")
            dirty = 1
            return

        # There are some priors.
        addr = this_dude[0].lower()
        hist = self.bounce_info[addr]
        difference = now - hist[0]
        if len(Utils.FindMatchingAddresses(addr, self.members)):
            if self.post_id - hist[2] > self.max_posts_between_bounces:
                # There's been enough posts since last bounce that we're
                # restarting.  (Might should keep track of who goes stale
                # how often.)
                syslog("bounce", report + "first fresh")
                self.bounce_info[addr] = [now, self.post_id, self.post_id]
                dirty = 1
                return
            self.bounce_info[addr][2] = self.post_id
            dirty = 1
            if ((self.post_id - hist[1] >
                 self.minimum_post_count_before_bounce_action)
                and
                (difference > self.minimum_removal_date * secs_per_day)):
                syslog("bounce", report + "exceeded limits")
                self.HandleBouncingAddress(addr, msg)
                return
            else:
                post_count = (self.minimum_post_count_before_bounce_action
                              - (self.post_id - hist[1]))
                if post_count < 0:
                    post_count = 0
                remain = (self.minimum_removal_date
                          * secs_per_day - difference)
                syslog("bounce", report + ("%d more allowed over %d secs"
                                           % (post_count, remain)))
                return

        elif len(Utils.FindMatchingAddresses(addr, self.digest_members)):
            if self.volume > hist[1]:
                syslog("bounce", "%s: first fresh (D)" %
                       self._internal_name)
                self.bounce_info[addr] = [now, self.volume, self.volume]
                return
            if difference > self.minimum_removal_date * secs_per_day:
                syslog("bounce", report + "exceeded limits (D)")
                self.HandleBouncingAddress(addr, msg)
                return 
            syslog("bounce", report + "digester lucked out")
        else:
            syslog("bounce", "%s: address %s not a member." %
                   (self.internal_name(), addr))

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
                negative=_("not ")
            else:
                negative=""
            recipient = self.GetAdminEmail()
            if addr in self.owner + [recipient]:
                # Whoops!  This is a bounce of a bounce notice - do not
                # perpetuate the bounce loop!  Log it prominently and be
                # satisfied with that.
                syslog("error",
                       "%s: Bounce recipient loop"
                       " encountered!\n\t%s\n\tBad admin recipient: %s" %
                       (self.internal_name(),
                        "(Ie, bounce notification addr, itself, bounces.)",
                        addr))
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
                    {'admin_url': self.GetScriptURL('admin', absolute=1),
                     }, lang=self.preferred_language)
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
                 }, lang=self.preferred_language)
            # add this here so it doesn't get wrapped/filled
            # FIXME
            text = text + '\n\n--' + boundary + \
                   '\nContent-type: text/plain; charset=' + Utils.GetCharSet()

            # We do this here so this text won't be wrapped.  note that
            # 'bounce.txt' has a trailing newline.  Be robust about getting
            # the body of the message.
            body = _('[original message unavailable]')
            try:
                body = msg.body
            except AttributeError:
                try:
                    msg.rewindbody()
                    body = msg.fp.read()
                except IOError:
                    pass
            # FIXME
            text += EMPTYSTRING.join(msg.headers) + '\n' + \
                    Utils.QuotePeriods(body) + '\n' + \
                   '--' + boundary + '--'

            if negative:
                negative = negative.upper()

            # send the bounce message
            rname = self.real_name
            msg = Message.UserNotification(
                recipient, mm_cfg.MAILMAN_OWNER,
                _('%(rname)s member %(addr)s bouncing - %(negative)s%(did)s'),
                text)
            msg['MIME-Version'] = '1.0'
            msg['Content-Type'] = 'multipart/mixed; boundary="%s"' % boundary
            msg.send(self)

    def DisableBouncingAddress(self, addr):
        """Disable delivery for bouncing user address.

        Returning success and notification status.
        """
        if not self.IsMember(addr):
            reason = _('User not found.')
            syslog("bounce", "%s: NOT disabled %s: %s" %
                   (self.real_name, addr, reason))
            return reason, 1
        try:
            if self.GetUserOption(addr, mm_cfg.DisableDelivery):
                # No need to send out notification if they're already disabled.
                syslog("bounce", "%s: already disabled %s" %
                       (self.real_name, addr))
                return 1, 0
            else:
                self.SetUserOption(addr, mm_cfg.DisableDelivery, 1)
                syslog("bounce", "%s: disabled %s" % (self.real_name, addr))
                self.Save()
                return 1, 1
        except Errors.MMNoSuchUserError:
            syslog("bounce", "%s: NOT disabled %s: %s" %
                   (self.real_name, addr, Errors.MMNoSuchUserError))
            self.ClearBounceInfo(addr)
            self.Save()
            return Errors.MMNoSuchUserError, 1
            
    def RemoveBouncingAddress(self, addr):
        """Unsubscribe user with bouncing address.

        Returning success and notification status."""
        if not self.IsMember(addr):
            reason = _('User not found.')
            syslog("bounce", "%s: NOT removed %s: %s" %
                   (self.real_name, addr, reason))
            return reason, 1
        try:
            self.DeleteMember(addr, "bouncing addr")
            syslog("bounce", "%s: removed %s" % (self.real_name, addr))
            self.Save()
            return 1, 1
        except Errors.MMNoSuchUserError:
            syslog("bounce", "%s: NOT removed %s: %s" %
                   (self.real_name, addr, Errors.MMNoSuchUserError))
            self.ClearBounceInfo(addr)
            self.Save()
            return Errors.MMNoSuchUserError, 1
