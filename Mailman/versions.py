# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
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


"""Routines which rectify an old mailing list with current structure.

The MailList.CheckVersion() method looks for an old .data_version setting in
the loaded structure, and if found calls the Update() routine from this
module, supplying the list and the state last loaded from storage.  The state
is necessary to distinguish from default assignments done in the .InitVars()
methods, before .CheckVersion() is called.

For new versions you should add sections to the UpdateOldVars() and the
UpdateOldUsers() sections, to preserve the sense of settings across structural
changes.  Note that the routines have only one pass - when .CheckVersions()
finds a version change it runs this routine and then updates the data_version
number of the list, and then does a .Save(), so the transformations won't be
run again until another version change is detected.

"""


import re
from types import ListType, StringType

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Message
from Mailman.MemberAdaptor import UNKNOWN
from Mailman.Logging.Syslog import syslog



def Update(l, stored_state):
    "Dispose of old vars and user options, mapping to new ones when suitable."
    ZapOldVars(l)
    NewVars(l)
    UpdateOldVars(l, stored_state)
    UpdateOldUsers(l)
    CanonicalizeUserOptions(l)
    NewRequestsDatabase(l)



def ZapOldVars(mlist):
    for name in ('num_spawns', 'filter_prog', 'clobber_date',
                 'public_archive_file_dir', 'private_archive_file_dir',
                 'archive_directory',
                 # Pre-2.1a4 bounce data
                 'minimum_removal_date',
                 'minimum_post_count_before_bounce_action',
                 'automatic_bounce_action',
                 'max_posts_between_bounces',
                 ):
        if hasattr(mlist, name):
            delattr(mlist, name)



uniqueval = []
def UpdateOldVars(l, stored_state):
    """Transform old variable values into new ones, deleting old ones.
    stored_state is last snapshot from file, as opposed to from InitVars()."""

    def PreferStored(oldname, newname, newdefault=uniqueval,
                     l=l, state=stored_state):
        """Use specified old value if new value is not in stored state.

        If the old attr does not exist, and no newdefault is specified, the
        new attr is *not* created - so either specify a default or be positive
        that the old attr exists - or don't depend on the new attr.

        """
        if hasattr(l, oldname):
            if not state.has_key(newname):
                setattr(l, newname, getattr(l, oldname))
            delattr(l, oldname)
        if not hasattr(l, newname) and newdefault is not uniqueval:
                setattr(l, newname, newdefault)

    # Migrate to 2.1b3, baw 17-Aug-2001
    if hasattr(l, 'dont_respond_to_post_requests'):
        oldval = getattr(l, 'dont_respond_to_post_requests')
        if not hasattr(l, 'respond_to_post_requests'):
            l.respond_to_post_requests = not oldval
        del l.dont_respond_to_post_requests

    # Migrate to 2.1b3, baw 13-Oct-2001
    # Basic defaults for new variables
    if not hasattr(l, 'default_member_moderation'):
        l.default_member_moderation = mm_cfg.DEFAULT_DEFAULT_MEMBER_MODERATION
    if not hasattr(l, 'accept_these_nonmembers'):
        l.accept_these_nonmembers = []
    if not hasattr(l, 'hold_these_nonmembers'):
        l.hold_these_nonmembers = []
    if not hasattr(l, 'reject_these_nonmembers'):
        l.reject_these_nonmembers = []
    if not hasattr(l, 'discard_these_nonmembers'):
        l.discard_these_nonmembers = []
    if not hasattr(l, 'forward_auto_discards'):
        l.forward_auto_discards = mm_cfg.DEFAULT_FORWARD_AUTO_DISCARDS
    if not hasattr(l, 'generic_nonmember_action'):
        l.generic_nonmember_action = mm_cfg.DEFAULT_GENERIC_NONMEMBER_ACTION
    # Now convert what we can...
    if hasattr(l, 'moderated'):
        # The closest we can get to the semantics of this variable is to set
        # the default member moderation flag, and to set the generic nonmember
        # action.
        oldval = getattr(l, 'moderated')
        # Flag values have the same semantic
        l.default_member_moderation = oldval
        # If we were moderating, then hold nonmember postings, otherwise
        # accept them.
        if oldval:
            l.generic_nonmember_action = 1
        else:
            l.generic_nonmember_action = 0
        del l.moderated
    if hasattr(l, 'forbidden_posters'):
        # For each of the posters on this list, if they are members, toggle on
        # their moderation flag.  If they are not members, then add them to
        # hold_these_nonmembers.
        forbiddens = l.forbidden_posters
        for addr in forbiddens:
            if l.isMember(addr):
                l.setMemberOption(addr, mm_cfg.Moderate, 1)
            else:
                l.hold_these_nonmembers.append(addr)
        del l.forbidden_posters
    if hasattr(l, 'posters'):
        # This is a fun one. :( The semantics of this and member_posting_only
        # is way too confusing, which is why we're getting rid of them here.
        # If there are posters and member_posting_only == yes, then posters
        # are members or non-members that we will automatically accept.  If
        # there are posters, but member_posting_only == no, then we will
        # automatically accept any members or non-members, but all other
        # member postings will be held for approval.  I think.
        posters = l.posters
        membersonly = l.member_posting_only
        if posters:
            if not membersonly:
                # Turn on the moderation bit of all the existing members, and
                # the default moderation bit
                l.default_member_moderation = 1
                for addr in l.getMembers():
                    l.setMemberOption(addr, mm_cfg.Moderate, 1)
            # Now turn off the moderation bit for all poster members, or add
            # non-members to auto-accept.
            for addr in posters:
                if l.isMember(addr):
                    l.setMemberOption(addr, mm_cfg.Moderate, 0)
                else:
                    l.accept_these_nonmembers.append(addr)
        del l.posters
        del l.member_posting_only

    # Migrate to 1.0b6, klm 10/22/1998:
    PreferStored('reminders_to_admins', 'umbrella_list',
                 mm_cfg.DEFAULT_UMBRELLA_LIST)

    # Migrate up to 1.0b5:
    PreferStored('auto_subscribe', 'open_subscribe')
    PreferStored('closed', 'private_roster')
    PreferStored('mimimum_post_count_before_removal',
                 'mimimum_post_count_before_bounce_action')
    PreferStored('bad_posters', 'forbidden_posters')
    PreferStored('automatically_remove', 'automatic_bounce_action')
    if hasattr(l, "open_subscribe"):
        if l.open_subscribe:
            if mm_cfg.ALLOW_OPEN_SUBSCRIBE:
                l.subscribe_policy = 0 
            else:
                l.subscribe_policy = 1
        else:
            l.subscribe_policy = 2      # admin approval
        delattr(l, "open_subscribe")
    if not hasattr(l, "administrivia"):
        setattr(l, "administrivia", mm_cfg.DEFAULT_ADMINISTRIVIA)
    if not hasattr(l, "admin_member_chunksize"):
        setattr(l, "admin_member_chunksize",
                mm_cfg.DEFAULT_ADMIN_MEMBER_CHUNKSIZE)
    #
    # this attribute was added then deleted, so there are a number of
    # cases to take care of
    #
    if hasattr(l, "posters_includes_members"): 
        if l.posters_includes_members:
            if l.posters:
                l.member_posting_only = 1
        else:
            if l.posters:
                l.member_posting_only = 0
        delattr(l, "posters_includes_members")
    elif l.data_version <= 10 and l.posters:
        # make sure everyone gets the behavior the list used to have, but only
        # for really old versions of Mailman (1.0b5 or before).  Any newer
        # version of Mailman should not get this attribute whacked.
        l.member_posting_only = 0
    #
    # transfer the list data type for holding members and digest members
    # to the dict data type starting file format version 11
    #
    if type(l.members) is ListType:
        members = {}
        for m in l.members:
            members[m] = 1
        l.members = members
    if type(l.digest_members) is ListType:
        dmembers = {}
        for dm in l.digest_members:
            dmembers[dm] = 1
        l.digest_members = dmembers
    #
    # set admin_notify_mchanges
    #
    if not hasattr(l, "admin_notify_mchanges"):
        setattr(l, "admin_notify_mchanges",
                mm_cfg.DEFAULT_ADMIN_NOTIFY_MCHANGES)
    #
    # Convert the members and digest_members addresses so that the keys of
    # both these are always lowercased, but if there is a case difference, the 
    # value contains the case preserved value
    #
    for k in l.members.keys():
        if k.lower() <> k:
            l.members[k.lower()] = Utils.LCDomain(k)
            del l.members[k]
        elif type(l.members[k]) == StringType and k == l.members[k].lower():
            # already converted
            pass
        else:
            l.members[k] = 0
    for k in l.digest_members.keys():
        if k.lower() <> k:
            l.digest_members[k.lower()] = Utils.LCDomain(k)
            del l.digest_members[k]
        elif type(l.digest_members[k]) == StringType and \
                 k == l.digest_members[k].lower():
            # already converted
            pass
        else:
            l.digest_members[k] = 0



def NewVars(l):
    """Add defaults for these new variables if they don't exist."""
    def add_only_if_missing(attr, initval, l=l):
        if not hasattr(l, attr):
            setattr(l, attr, initval)
    # 1.2 beta 1, baw 18-Feb-2000
    # Autoresponder mixin class attributes
    add_only_if_missing('autorespond_postings', 0)
    add_only_if_missing('autorespond_admin', 0)
    add_only_if_missing('autorespond_requests', 0)
    add_only_if_missing('autoresponse_postings_text', '')
    add_only_if_missing('autoresponse_admin_text', '')
    add_only_if_missing('autoresponse_request_text', '')
    add_only_if_missing('autoresponse_graceperiod', 90)
    add_only_if_missing('postings_responses', {})
    add_only_if_missing('admin_responses', {})
    add_only_if_missing('reply_goes_to_list', '')
    add_only_if_missing('preferred_language', mm_cfg.DEFAULT_SERVER_LANGUAGE)
    add_only_if_missing('available_languages', [])
    add_only_if_missing('digest_volume_frequency',
                        mm_cfg.DEFAULT_DIGEST_VOLUME_FREQUENCY)
    add_only_if_missing('digest_last_sent_at', 0)
    add_only_if_missing('mod_password', None)
    add_only_if_missing('moderator', [])
    add_only_if_missing('topics', [])
    add_only_if_missing('topics_enabled', 0)
    add_only_if_missing('topics_bodylines_limit', 5)
    add_only_if_missing('one_last_digest', {})
    add_only_if_missing('usernames', {})
    add_only_if_missing('personalize', 0)
    add_only_if_missing('first_strip_reply_to',
                        mm_cfg.DEFAULT_FIRST_STRIP_REPLY_TO)
    add_only_if_missing('unsubscribe_policy',
                        mm_cfg.DEFAULT_UNSUBSCRIBE_POLICY)
    add_only_if_missing('send_goodbye_msg', mm_cfg.DEFAULT_SEND_GOODBYE_MSG)
    add_only_if_missing('include_rfc2369_headers', 1)
    add_only_if_missing('bounce_score_threshold',
                        mm_cfg.DEFAULT_BOUNCE_SCORE_THRESHOLD)
    add_only_if_missing('bounce_info_stale_after',
                        mm_cfg.DEFAULT_BOUNCE_INFO_STALE_AFTER)
    add_only_if_missing('bounce_you_are_disabled_warnings',
                        mm_cfg.DEFAULT_BOUNCE_YOU_ARE_DISABLED_WARNINGS)
    add_only_if_missing(
        'bounce_you_are_disabled_warnings_interval',
        mm_cfg.DEFAULT_BOUNCE_YOU_ARE_DISABLED_WARNINGS_INTERVAL)
    add_only_if_missing('ban_list', [])



def UpdateOldUsers(l):
    """Transform sense of changed user options."""
    # pre-1.0b11 to 1.0b11.  Force all keys in l.passwords to be lowercase
    passwords = {}
    for k, v in l.passwords.items():
        passwords[k.lower()] = v
    l.passwords = passwords
    # Clear out bounce_info; we're going to do things completely differently
    l.bounce_info = {}



def CanonicalizeUserOptions(l):
    """Fix up the user options."""
    # pre 1.0rc2 to 1.0rc3.  For all keys in l.user_options to be lowercase,
    # but merge options for both cases
    options = {}
    for k, v in l.user_options.items():
        if k is None:
            continue
        lcuser = k.lower()
        flags = 0
        if options.has_key(lcuser):
            flags = options[lcuser]
        flags |= v
        options[lcuser] = flags
    l.user_options = options
    # 2.1alpha3 -> 2.1alpha4.  The DisableDelivery flag is now moved into
    # get/setDeilveryStatus().  This must be done after the addresses are
    # canonicalized.
    l.delivery_status = {}
    for k, v in l.user_options.items():
        if l.getMemberOption(k, mm_cfg.DisableDelivery):
            # Convert this flag into a legacy disable
            l.setDeliveryStatus(k, UNKNOWN)
            l.setMemberOption(k, mm_cfg.DisableDelivery, 0)



def NewRequestsDatabase(l):
    """With version 1.2, we use a new pending request database schema."""
    r = getattr(l, 'requests', {})
    if not r:
        # no old-style requests
        return
    for k, v in r.items():
        if k == 'post':
            # This is a list of tuples with the following format
            #
            # a sequential request id integer
            # a timestamp float
            # a message tuple: (author-email-str, message-text-str)
            # a reason string
            # the subject string
            #
            # We'll re-submit this as a new HoldMessage request, but we'll
            # blow away the original timestamp and request id.  This means the
            # request will live a little longer than it possibly should have,
            # but that's no big deal.
            for p in v:
                author, text = p[2]
                reason = p[3]
                msg = Message.OutgoingMessage(text)
                l.HoldMessage(msg, reason)
            del r[k]
        elif k == 'add_member':
            # This is a list of tuples with the following format
            #
            # a sequential request id integer
            # a timestamp float
            # a digest flag (0 == nodigest, 1 == digest)
            # author-email-str
            # password
            #
            # See the note above; the same holds true.
            for ign, ign, digest, addr, password in v:
                l.HoldSubscription(addr, password, digest)
            del r[k]
        else:
            syslog('error', """\
VERY BAD NEWS.  Unknown pending request type `%s' found for list: %s""",
                   k, l.internal_name())
