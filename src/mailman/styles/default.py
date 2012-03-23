# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Application of list styles to new and existing lists."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DefaultStyle',
    ]


# XXX Styles need to be reconciled with lazr.config.

import datetime

from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.action import Action, FilterAction
from mailman.interfaces.bounce import UnrecognizedBounceDisposition
from mailman.interfaces.digests import DigestFrequency
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.mailinglist import Personalization, ReplyToMunging
from mailman.interfaces.nntp import NewsModeration
from mailman.interfaces.styles import IStyle



class DefaultStyle:
    """The default (i.e. legacy) style."""

    implements(IStyle)

    name = 'default'
    priority = 0    # the lowest priority style

    def apply(self, mailing_list):
        """See `IStyle`."""
        # For cut-n-paste convenience.
        mlist = mailing_list
        # List identity.
        mlist.display_name = mlist.list_name.capitalize()
        mlist.list_id = '{0.list_name}.{0.mail_host}'.format(mlist)
        mlist.include_rfc2369_headers = True
        mlist.include_list_post_header = True
        # Most of these were ripped from the old MailList.InitVars() method.
        mlist.volume = 1
        mlist.post_id = 1
        mlist.new_member_options = 256
        mlist.respond_to_post_requests = True
        mlist.advertised = True
        mlist.max_num_recipients = 10
        mlist.max_message_size = 40 # KB
        mlist.reply_goes_to_list = ReplyToMunging.no_munging
        mlist.reply_to_address = ''
        mlist.first_strip_reply_to = False
        mlist.admin_immed_notify = True
        mlist.admin_notify_mchanges = False
        mlist.require_explicit_destination = True
        mlist.send_reminders = True
        mlist.send_welcome_message = True
        mlist.send_goodbye_message = True
        mlist.bounce_matching_headers = """
# Lines that *start* with a '#' are comments.
to: friend@public.com
message-id: relay.comanche.denmark.eu
from: list@listme.com
from: .*@uplinkpro.com
"""
        mlist.header_matches = []
        mlist.anonymous_list = False
        mlist.description = ''
        mlist.info = ''
        mlist.welcome_message_uri = 'mailman:///welcome.txt'
        mlist.goodbye_message_uri = ''
        mlist.subscribe_policy = 1
        mlist.subscribe_auto_approval = []
        mlist.unsubscribe_policy = 0
        mlist.private_roster = 1
        mlist.obscure_addresses = True
        mlist.admin_member_chunksize = 30
        mlist.administrivia = True
        mlist.preferred_language = 'en'
        mlist.collapse_alternatives = True
        mlist.convert_html_to_plaintext = False
        mlist.filter_action = FilterAction.discard
        mlist.filter_content = False
        # Digest related variables
        mlist.digestable = True
        mlist.digest_is_default = False
        mlist.mime_is_default_digest = False
        mlist.digest_size_threshold = 30 # KB
        mlist.digest_send_periodic = True
        mlist.digest_header_uri = None
        mlist.digest_footer_uri = (
            'mailman:///$listname/$language/footer-generic.txt')
        mlist.digest_volume_frequency = DigestFrequency.monthly
        mlist.next_digest_number = 1
        mlist.nondigestable = True
        mlist.personalize = Personalization.none
        # New sender-centric moderation (privacy) options
        mlist.default_member_action = Action.defer
        mlist.default_nonmember_action = Action.hold
        # Archiver
        mlist.archive = True
        mlist.archive_private = 0
        mlist.archive_volume_frequency = 1
        mlist.emergency = False
        mlist.member_moderation_notice = ''
        mlist.accept_these_nonmembers = []
        mlist.hold_these_nonmembers = []
        mlist.reject_these_nonmembers = []
        mlist.discard_these_nonmembers = []
        mlist.forward_auto_discards = True
        mlist.generic_nonmember_action = 1
        mlist.nonmember_rejection_notice = ''
        # Max autoresponses per day.  A mapping between addresses and a
        # 2-tuple of the date of the last autoresponse and the number of
        # autoresponses sent on that date.
        mlist.subject_prefix = _('[$mlist.display_name] ')
        mlist.header_uri = None
        mlist.footer_uri = 'mailman:///$listname/$language/footer-generic.txt'
        # Set this to Never if the list's preferred language uses us-ascii,
        # otherwise set it to As Needed.
        if mlist.preferred_language.charset == 'us-ascii':
            mlist.encode_ascii_prefixes = 0
        else:
            mlist.encode_ascii_prefixes = 2
        # scrub regular delivery
        mlist.scrub_nondigest = False
        # automatic discarding
        mlist.max_days_to_hold = 0
        # Autoresponder
        mlist.autorespond_owner = ResponseAction.none
        mlist.autoresponse_owner_text = ''
        mlist.autorespond_postings = ResponseAction.none
        mlist.autoresponse_postings_text = ''
        mlist.autorespond_requests = ResponseAction.none
        mlist.autoresponse_request_text = ''
        mlist.autoresponse_grace_period = datetime.timedelta(days=90)
        # Bounces
        mlist.forward_unrecognized_bounces_to = (
            UnrecognizedBounceDisposition.administrators)
        mlist.process_bounces = True
        mlist.bounce_score_threshold = 5.0
        mlist.bounce_info_stale_after = datetime.timedelta(days=7)
        mlist.bounce_you_are_disabled_warnings = 3
        mlist.bounce_you_are_disabled_warnings_interval = (
            datetime.timedelta(days=7))
        mlist.bounce_notify_owner_on_disable = True
        mlist.bounce_notify_owner_on_removal = True
        # This holds legacy member related information.  It's keyed by the
        # member address, and the value is an object containing the bounce
        # score, the date of the last received bounce, and a count of the
        # notifications left to send.
        mlist.bounce_info = {}
        # New style delivery status
        mlist.delivery_status = {}
        # NNTP gateway
        mlist.nntp_host = ''
        mlist.linked_newsgroup = ''
        mlist.gateway_to_news = False
        mlist.gateway_to_mail = False
        mlist.news_prefix_subject_too = True
        # In patch #401270, this was called newsgroup_is_moderated, but the
        # semantics weren't quite the same.
        mlist.news_moderation = NewsModeration.none
        # Topics
        #
        # `topics' is a list of 4-tuples of the following form:
        #
        #     (name, pattern, description, emptyflag)
        #
        # name is a required arbitrary string displayed to the user when they
        # get to select their topics of interest
        #
        # pattern is a required verbose regular expression pattern which is
        # used as IGNORECASE.
        #
        # description is an optional description of what this topic is
        # supposed to match
        #
        # emptyflag is a boolean used internally in the admin interface to
        # signal whether a topic entry is new or not (new ones which do not
        # have a name or pattern are not saved when the submit button is
        # pressed).
        mlist.topics = []
        mlist.topics_enabled = False
        mlist.topics_bodylines_limit = 5
        # This is a mapping between user "names" (i.e. addresses) and
        # information about which topics that user is interested in.  The
        # values are a list of topic names that the user is interested in,
        # which should match the topic names in mlist.topics above.
        #
        # If the user has not selected any topics of interest, then the rule
        # is that they will get all messages, and they will not have an entry
        # in this dictionary.
        mlist.topics_userinterest = {}
        # The processing chain that messages posted to this mailing list get
        # processed by.
        mlist.posting_chain = 'default-posting-chain'
        # The default pipeline to send accepted messages through to the
        # mailing list's members.
        mlist.posting_pipeline = 'default-posting-pipeline'
        # The processing chain that messages posted to this mailing list's
        # -owner address gets processed by.
        mlist.owner_chain = 'default-owner-chain'
        # The default pipeline to send -owner email through.
        mlist.owner_pipeline = 'default-owner-pipeline'

    def match(self, mailing_list, styles):
        """See `IStyle`."""
        # If no other styles have matched, then the default style matches.
        if len(styles) == 0:
            styles.append(self)
