# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Application of list styles to new and existing lists."""

__metaclass__ = type
__all__ = [
    'DefaultStyle',
    'style_manager',
    ]

import datetime

from operator import attrgetter
from zope.interface import implements
from zope.interface.verify import verifyObject

from Mailman import Utils
from Mailman.app.plugins import get_plugins
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.interfaces import (
    Action, DuplicateStyleError, IStyle, IStyleManager, NewsModeration,
    Personalization)



class DefaultStyle:
    """The defalt (i.e. legacy) style."""

    implements(IStyle)

    name = 'default'
    priority = 0    # the lowest priority style

    def apply(self, mailing_list):
        """See `IStyle`."""
        # For cut-n-paste convenience.
        mlist = mailing_list
        # Most of these were ripped from the old MailList.InitVars() method.
        mlist.volume = 1
        mlist.post_id = 1
        mlist.new_member_options = config.DEFAULT_NEW_MEMBER_OPTIONS
        # This stuff is configurable
        mlist.real_name = mlist.list_name.capitalize()
        mlist.respond_to_post_requests = True
        mlist.advertised = config.DEFAULT_LIST_ADVERTISED
        mlist.max_num_recipients = config.DEFAULT_MAX_NUM_RECIPIENTS
        mlist.max_message_size = config.DEFAULT_MAX_MESSAGE_SIZE
        mlist.reply_goes_to_list = config.DEFAULT_REPLY_GOES_TO_LIST
        mlist.reply_to_address = u''
        mlist.first_strip_reply_to = config.DEFAULT_FIRST_STRIP_REPLY_TO
        mlist.admin_immed_notify = config.DEFAULT_ADMIN_IMMED_NOTIFY
        mlist.admin_notify_mchanges = (
            config.DEFAULT_ADMIN_NOTIFY_MCHANGES)
        mlist.require_explicit_destination = (
            config.DEFAULT_REQUIRE_EXPLICIT_DESTINATION)
        mlist.acceptable_aliases = config.DEFAULT_ACCEPTABLE_ALIASES
        mlist.send_reminders = config.DEFAULT_SEND_REMINDERS
        mlist.send_welcome_msg = config.DEFAULT_SEND_WELCOME_MSG
        mlist.send_goodbye_msg = config.DEFAULT_SEND_GOODBYE_MSG
        mlist.bounce_matching_headers = (
            config.DEFAULT_BOUNCE_MATCHING_HEADERS)
        mlist.header_matches = []
        mlist.anonymous_list = config.DEFAULT_ANONYMOUS_LIST
        mlist.description = u''
        mlist.info = u''
        mlist.welcome_msg = u''
        mlist.goodbye_msg = u''
        mlist.subscribe_policy = config.DEFAULT_SUBSCRIBE_POLICY
        mlist.subscribe_auto_approval = config.DEFAULT_SUBSCRIBE_AUTO_APPROVAL
        mlist.unsubscribe_policy = config.DEFAULT_UNSUBSCRIBE_POLICY
        mlist.private_roster = config.DEFAULT_PRIVATE_ROSTER
        mlist.obscure_addresses = config.DEFAULT_OBSCURE_ADDRESSES
        mlist.admin_member_chunksize = config.DEFAULT_ADMIN_MEMBER_CHUNKSIZE
        mlist.administrivia = config.DEFAULT_ADMINISTRIVIA
        mlist.preferred_language = config.DEFAULT_SERVER_LANGUAGE
        mlist.include_rfc2369_headers = True
        mlist.include_list_post_header = True
        mlist.filter_mime_types = config.DEFAULT_FILTER_MIME_TYPES
        mlist.pass_mime_types = config.DEFAULT_PASS_MIME_TYPES
        mlist.filter_filename_extensions = (
            config.DEFAULT_FILTER_FILENAME_EXTENSIONS)
        mlist.pass_filename_extensions = config.DEFAULT_PASS_FILENAME_EXTENSIONS
        mlist.filter_content = config.DEFAULT_FILTER_CONTENT
        mlist.collapse_alternatives = config.DEFAULT_COLLAPSE_ALTERNATIVES
        mlist.convert_html_to_plaintext = (
            config.DEFAULT_CONVERT_HTML_TO_PLAINTEXT)
        mlist.filter_action = config.DEFAULT_FILTER_ACTION
        # Digest related variables
        mlist.digestable = config.DEFAULT_DIGESTABLE
        mlist.digest_is_default = config.DEFAULT_DIGEST_IS_DEFAULT
        mlist.mime_is_default_digest = config.DEFAULT_MIME_IS_DEFAULT_DIGEST
        mlist.digest_size_threshhold = config.DEFAULT_DIGEST_SIZE_THRESHHOLD
        mlist.digest_send_periodic = config.DEFAULT_DIGEST_SEND_PERIODIC
        mlist.digest_header = config.DEFAULT_DIGEST_HEADER
        mlist.digest_footer = config.DEFAULT_DIGEST_FOOTER
        mlist.digest_volume_frequency = config.DEFAULT_DIGEST_VOLUME_FREQUENCY
        mlist.one_last_digest = {}
        mlist.digest_members = {}
        mlist.next_digest_number = 1
        mlist.nondigestable = config.DEFAULT_NONDIGESTABLE
        mlist.personalize = Personalization.none
        # New sender-centric moderation (privacy) options
        mlist.default_member_moderation = (
            config.DEFAULT_DEFAULT_MEMBER_MODERATION)
        # Archiver
        mlist.archive = config.DEFAULT_ARCHIVE
        mlist.archive_private = config.DEFAULT_ARCHIVE_PRIVATE
        mlist.archive_volume_frequency = (
            config.DEFAULT_ARCHIVE_VOLUME_FREQUENCY)
        mlist.emergency = False
        mlist.member_moderation_action = Action.hold
        mlist.member_moderation_notice = u''
        mlist.accept_these_nonmembers = []
        mlist.hold_these_nonmembers = []
        mlist.reject_these_nonmembers = []
        mlist.discard_these_nonmembers = []
        mlist.forward_auto_discards = config.DEFAULT_FORWARD_AUTO_DISCARDS
        mlist.generic_nonmember_action = (
            config.DEFAULT_GENERIC_NONMEMBER_ACTION)
        mlist.nonmember_rejection_notice = u''
        # Ban lists
        mlist.ban_list = []
        # Max autoresponses per day.  A mapping between addresses and a
        # 2-tuple of the date of the last autoresponse and the number of
        # autoresponses sent on that date.
        mlist.hold_and_cmd_autoresponses = {}
        mlist.subject_prefix = _(config.DEFAULT_SUBJECT_PREFIX)
        mlist.msg_header = config.DEFAULT_MSG_HEADER
        mlist.msg_footer = config.DEFAULT_MSG_FOOTER
        # Set this to Never if the list's preferred language uses us-ascii,
        # otherwise set it to As Needed
        if Utils.GetCharSet(mlist.preferred_language) == 'us-ascii':
            mlist.encode_ascii_prefixes = 0
        else:
            mlist.encode_ascii_prefixes = 2
        # scrub regular delivery
        mlist.scrub_nondigest = config.DEFAULT_SCRUB_NONDIGEST
        # automatic discarding
        mlist.max_days_to_hold = config.DEFAULT_MAX_DAYS_TO_HOLD
        # Autoresponder
        mlist.autorespond_postings = False
        mlist.autorespond_admin = False
        # this value can be
        #  0 - no autoresponse on the -request line
        #  1 - autorespond, but discard the original message
        #  2 - autorespond, and forward the message on to be processed
        mlist.autorespond_requests = 0
        mlist.autoresponse_postings_text = u''
        mlist.autoresponse_admin_text = u''
        mlist.autoresponse_request_text = u''
        mlist.autoresponse_graceperiod = datetime.timedelta(days=90)
        mlist.postings_responses = {}
        mlist.admin_responses = {}
        mlist.request_responses = {}
        # Bounces
        mlist.bounce_processing = config.DEFAULT_BOUNCE_PROCESSING
        mlist.bounce_score_threshold = config.DEFAULT_BOUNCE_SCORE_THRESHOLD
        mlist.bounce_info_stale_after = config.DEFAULT_BOUNCE_INFO_STALE_AFTER
        mlist.bounce_you_are_disabled_warnings = (
            config.DEFAULT_BOUNCE_YOU_ARE_DISABLED_WARNINGS)
        mlist.bounce_you_are_disabled_warnings_interval = (
            config.DEFAULT_BOUNCE_YOU_ARE_DISABLED_WARNINGS_INTERVAL)
        mlist.bounce_unrecognized_goes_to_list_owner = (
            config.DEFAULT_BOUNCE_UNRECOGNIZED_GOES_TO_LIST_OWNER)
        mlist.bounce_notify_owner_on_disable = (
            config.DEFAULT_BOUNCE_NOTIFY_OWNER_ON_DISABLE)
        mlist.bounce_notify_owner_on_removal = (
            config.DEFAULT_BOUNCE_NOTIFY_OWNER_ON_REMOVAL)
        # This holds legacy member related information.  It's keyed by the
        # member address, and the value is an object containing the bounce
        # score, the date of the last received bounce, and a count of the
        # notifications left to send.
        mlist.bounce_info = {}
        # New style delivery status
        mlist.delivery_status = {}
        # NNTP gateway
        mlist.nntp_host = config.DEFAULT_NNTP_HOST
        mlist.linked_newsgroup = u''
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
        # The processing chain that messages coming into this list get
        # processed by.
        mlist.start_chain = u'built-in'
        # The default pipeline to send accepted messages through.
        mlist.pipeline = u'built-in'

    def match(self, mailing_list, styles):
        """See `IStyle`."""
        # If no other styles have matched, then the default style matches.
        if len(styles) == 0:
            styles.append(self)



class StyleManager:
    """The built-in style manager."""

    implements(IStyleManager)

    def __init__(self):
        """Install all styles from registered plugins, and install them."""
        self._styles = {}
        # Install all the styles provided by plugins.
        for style_factory in get_plugins('mailman.styles'):
            style = style_factory()
            # Let DuplicateStyleErrors percolate up.
            self.register(style)

    def get(self, name):
        """See `IStyleManager`."""
        return self._styles.get(name)

    def lookup(self, mailing_list):
        """See `IStyleManager`."""
        matched_styles = []
        for style in self.styles:
            style.match(mailing_list, matched_styles)
        for style in matched_styles:
            yield style

    @property
    def styles(self):
        """See `IStyleManager`."""
        for style in sorted(self._styles.values(),
                            key=attrgetter('priority'),
                            reverse=True):
            yield style

    def register(self, style):
        """See `IStyleManager`."""
        verifyObject(IStyle, style)
        if style.name in self._styles:
            raise DuplicateStyleError(style.name)
        self._styles[style.name] = style

    def unregister(self, style):
        """See `IStyleManager`."""
        # Let KeyErrors percolate up.
        del self._styles[style.name]



style_manager = StyleManager()
