# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""MailList mixin class managing the general options.
"""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.i18n import _



class General:
    def GetConfigCategory(self):
        return 'general', _('General Options')

    def GetConfigInfo(self, mlist, category, subcat):
        if category <> 'general':
            return None
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            _('''Fundamental list characteristics, including descriptive
            info and basic behaviors.'''),

            _('General list personality'),

            ('real_name', mm_cfg.String, WIDTH, 0,
             _('The public name of this list (make case-changes only).'),
             _('''The capitalization of this name can be changed to make it
             presentable in polite company as a proper noun, or to make an
             acronym part all upper case, etc.  However, the name will be
             advertised as the email address (e.g., in subscribe confirmation
             notices), so it should <em>not</em> be otherwise altered.  (Email
             addresses are not case sensitive, but they are sensitive to
             almost everything else :-)''')),

            ('owner', mm_cfg.EmailList, (3, WIDTH), 0,
             _("""The list administrator email addresses.  Multiple
             administrator addresses, each on separate line is okay."""),

             _('''There are two ownership roles associated with each mailing
             list.  The <em>list administrators</em> are the people who have
             ultimate control over all parameters of this mailing list.  They
             are able to change any list configuration variable available
             through these administration web pages.

             <p>The <em>list moderators</em> have more limited permissions;
             they are not able to change any list configuration variable, but
             they are allowed to tend to pending administration requests,
             including approving or rejecting held subscription requests, and
             disposing of held postings.  Of course, the <em>list
             administrators</em> can also tend to pending requests.

             <p>In order to split the list ownership duties into
             administrators and moderators, you must
             <a href="general#passwords">set a separate moderator password</a>,
             and also provide the <a href="?VARHELP=general/moderator">email
             addresses of the list moderators</a>.  Note that the field you
             are changing here specifies the list administators.''')),

            ('moderator', mm_cfg.EmailList, (3, WIDTH), 0,
             _("""The list moderator email addresses.  Multiple
             moderator addresses, each on separate line is okay."""),

             _('''There are two ownership roles associated with each mailing
             list.  The <em>list administrators</em> are the people who have
             ultimate control over all parameters of this mailing list.  They
             are able to change any list configuration variable available
             through these administration web pages.

             <p>The <em>list moderators</em> have more limited permissions;
             they are not able to change any list configuration variable, but
             they are allowed to tend to pending administration requests,
             including approving or rejecting held subscription requests, and
             disposing of held postings.  Of course, the <em>list
             administrators</em> can also tend to pending requests.

             <p>In order to split the list ownership duties into
             administrators and moderators, you must
             <a href="general#passwords">set a separate moderator password</a>,
             and also provide the email addresses of the list moderators in
             this section.  Note that the field you are changing here
             specifies the list moderators.''')),

            ('description', mm_cfg.String, WIDTH, 0,
             _('A terse phrase identifying this list.'),

             _('''This description is used when the mailing list is listed with
                other mailing lists, or in headers, and so forth.  It should
                be as succinct as you can get it, while still identifying what
                the list is.''')),

            ('info', mm_cfg.Text, (7, WIDTH), 0,
             _('''An introductory description - a few paragraphs - about the
             list.  It will be included, as html, at the top of the listinfo
             page.  Carriage returns will end a paragraph - see the details
             for more info.'''),
             _("""The text will be treated as html <em>except</em> that
             newlines will be translated to &lt;br&gt; - so you can use links,
             preformatted text, etc, but don't put in carriage returns except
             where you mean to separate paragraphs.  And review your changes -
             bad html (like some unterminated HTML constructs) can prevent
             display of the entire listinfo page.""")),

            ('subject_prefix', mm_cfg.String, WIDTH, 0,
             _('Prefix for subject line of list postings.'),
             _("""This text will be prepended to subject lines of messages
             posted to the list, to distinguish mailing list messages in in
             mailbox summaries.  Brevity is premium here, it's ok to shorten
             long mailing list names to something more concise, as long as it
             still identifies the mailing list.""")),

            ('welcome_msg', mm_cfg.Text, (4, WIDTH), 0,
             _('''List-specific text prepended to new-subscriber welcome
             message'''),

             _("""This value, if any, will be added to the front of the
             new-subscriber welcome message.  The rest of the welcome message
             already describes the important addresses and URLs for the
             mailing list, so you don't need to include any of that kind of
             stuff here.  This should just contain mission-specific kinds of
             things, like etiquette policies or team orientation, or that kind
             of thing.

             <p>Note that this text will be wrapped, according to the
             following rules:
             <ul><li>Each paragraph is filled so that no line is longer than
                     70 characters.
                 <li>Any line that begins with whitespace is not filled.
                 <li>A blank line separates paragraphs.
             </ul>""")),

            ('goodbye_msg', mm_cfg.Text, (4, WIDTH), 0,
             _('''Text sent to people leaving the list.  If empty, no special
             text will be added to the unsubscribe message.''')),

            _('''<tt>Reply-To:</tt> header munging'''),

            ('first_strip_reply_to', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''Before adding a list-specific <tt>Reply-To:</tt> header,
             should any existing <tt>Reply-To:</tt> field be stripped from
             the message?''')),

            ('reply_goes_to_list', mm_cfg.Radio,
             (_('Poster'), _('This list'), _('Explicit address')), 0,
             _('''Where are replies to list messages directed?
             <tt>Poster</tt> is <em>strongly</em> recommended for most mailing
             lists.'''),

             # Details for reply_goes_to_list
             _("""This option controls what Mailman does to the
             <tt>Reply-To:</tt> header in messages flowing through this
             mailing list.  When set to <em>Poster</em>, no <tt>Reply-To:</tt>
             header is added by Mailman, although if one is present in the
             original message, it is not stripped.  Setting this value to
             either <em>This list</em> or <em>Explicit address</em> causes
             Mailman to insert a specific <tt>Reply-To:</tt> header in all
             messages, overriding the header in the original message if
             necessary (<em>Explicit address</em> inserts the value of <a
             href="?VARHELP=general/reply_to_address">reply_to_address</a>).
 
             <p>There are many reasons not to introduce or override the
             <tt>Reply-To:</tt> header.  One is that some posters depend on
             their own <tt>Reply-To:</tt> settings to convey their valid
             return address.  Another is that modifying <tt>Reply-To:</tt>
             makes it much more difficult to send private replies.  See <a
             href="http://www.unicom.com/pw/reply-to-harmful.html">`Reply-To'
             Munging Considered Harmful</a> for a general discussion of this
             issue.  See <a
        href="http://www.metasystema.org/essays/reply-to-useful.mhtml">Reply-To
             Munging Considered Useful</a> for a dissenting opinion.

             <p>Some mailing lists have restricted posting privileges, with a
             parallel list devoted to discussions.  Examples are `patches' or
             `checkin' lists, where software changes are posted by a revision
             control system, but discussion about the changes occurs on a
             developers mailing list.  To support these types of mailing
             lists, select <tt>Explicit address</tt> and set the
             <tt>Reply-To:</tt> address below to point to the parallel
             list.""")),

            ('reply_to_address', mm_cfg.Email, WIDTH, 0,
             _('Explicit <tt>Reply-To:</tt> header.'),
             # Details for reply_to_address
             _("""This is the address set in the <tt>Reply-To:</tt> header
             when the <a
             href="?VARHELP=general/reply_goes_to_list">reply_goes_to_list</a>
             option is set to <em>Explicit address</em>.

             <p>There are many reasons not to introduce or override the
             <tt>Reply-To:</tt> header.  One is that some posters depend on
             their own <tt>Reply-To:</tt> settings to convey their valid
             return address.  Another is that modifying <tt>Reply-To:</tt>
             makes it much more difficult to send private replies.  See <a
             href="http://www.unicom.com/pw/reply-to-harmful.html">`Reply-To'
             Munging Considered Harmful</a> for a general discussion of this
             issue.  See <a
        href="http://www.metasystema.org/essays/reply-to-useful.mhtml">Reply-To
             Munging Considered Useful</a> for a dissenting opinion.

             <p>Some mailing lists have restricted posting privileges, with a
             parallel list devoted to discussions.  Examples are `patches' or
             `checkin' lists, where software changes are posted by a revision
             control system, but discussion about the changes occurs on a
             developers mailing list.  To support these types of mailing
             lists, specify the explicit <tt>Reply-To:</tt> address here.  You
             must also specify <tt>Explicit address</tt> in the
             <tt>reply_goes_to_list</tt>
             variable.

             <p>Note that if the original message contains a
             <tt>Reply-To:</tt> header, it will not be changed.""")),

            _('Umbrella list settings'),

            ('umbrella_list', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''Send password reminders to, eg, "-owner" address instead of
             directly to user.'''),

             _("""Set this to yes when this list is intended to cascade only
             to other mailing lists.  When set, meta notices like
             confirmations and password reminders will be directed to an
             address derived from the member\'s address - it will have the
             value of "umbrella_member_suffix" appended to the member's
             account name.""")),

            ('umbrella_member_suffix', mm_cfg.String, WIDTH, 0,
             _('''Suffix for use when this list is an umbrella for other
             lists, according to setting of previous "umbrella_list"
             setting.'''),

             _("""When "umbrella_list" is set to indicate that this list has
             other mailing lists as members, then administrative notices like
             confirmations and password reminders need to not be sent to the
             member list addresses, but rather to the owner of those member
             lists.  In that case, the value of this setting is appended to
             the member's account name for such notices.  `-owner' is the
             typical choice.  This setting has no effect when "umbrella_list"
             is "No".""")),

            _('Notifications'),

            ('send_reminders', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''Send monthly password reminders or no? Overrides the
             previous option.''')),

            ('send_welcome_msg', mm_cfg.Radio, (_('No'), _('Yes')), 0, 
             _('Send welcome message when people subscribe?'),
             _("""Turn this on only if you plan on subscribing people manually
             and don't want them to know that you did so.  This option is most
             useful for transparently migrating lists from some other mailing
             list manager to Mailman.""")),

            ('admin_immed_notify', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''Should the list moderators get immediate notice of new
             requests, as well as daily notices about collected ones?'''),

             _('''List moderators (and list administrators) are sent daily
             reminders of requests pending approval, like subscriptions to a
             moderated list, or postings that are being held for one reason or
             another.  Setting this option causes notices to be sent
             immediately on the arrival of new requests as well.''')),

            ('admin_notify_mchanges', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''Should administrator get notices of subscribes and
             unsubscribes?''')),
            
            ('respond_to_post_requests', mm_cfg.Radio,
             (_('No'), _('Yes')), 0,
             _('Send mail to poster when their posting is held for approval?'),

             _("""Approval notices are sent when mail triggers certain of the
             limits <em>except</em> routine list moderation and spam filters,
             for which notices are <em>not</em> sent.  This option overrides
             ever sending the notice.""")),

            _('Additional settings'),

            ('administrivia', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''(Administrivia filter) Check postings and intercept ones
             that seem to be administrative requests?'''),

             _("""Administrivia tests will check postings to see whether it's
             really meant as an administrative request (like subscribe,
             unsubscribe, etc), and will add it to the the administrative
             requests queue, notifying the administrator of the new request,
             in the process.""")),

            ('max_message_size', mm_cfg.Number, 7, 0,
             _('''Maximum length in kilobytes (KB) of a message body.  Use 0
             for no limit.''')),

            ('host_name', mm_cfg.Host, WIDTH, 0,
             _('Host name this list prefers for email.'),

             _("""The "host_name" is the preferred name for email to
             mailman-related addresses on this host, and generally should be
             the mail host's exchanger address, if any.  This setting can be
             useful for selecting among alternative names of a host that has
             multiple addresses.""")),

          ]
