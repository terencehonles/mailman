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

"""MailList mixin class managing the privacy options.
"""

from Mailman import mm_cfg
from Mailman.i18n import _



class Privacy:
    def GetConfigCategory(self):
        return 'privacy', _('Privacy options')

    def GetConfigInfo(self, mlist):
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        if mm_cfg.ALLOW_OPEN_SUBSCRIBE:
            sub_cfentry = ('subscribe_policy', mm_cfg.Radio,
                           # choices
                           (_('none'),
                            _('confirm'),
                            _('require approval'),
                            _('confirm+approval')),
                           0, 
                           _('What steps are required for subscription?<br>'),
                           _('''None - no verification steps (<em>Not
                           Recommended </em>)<br>
                           confirm (*) - email confirmation step required <br>
                           require approval - require list administrator
                           approval for subscriptions <br>
                           confirm+approval - both confirm and approve
                           
                           <p>(*) when someone requests a subscription,
                           Mailman sends them a notice with a unique
                           subscription request number that they must reply to
                           in order to subscribe.<br>

                           This prevents mischievous (or malicious) people
                           from creating subscriptions for others without
                           their consent.'''))
        else:
            sub_cfentry = ('subscribe_policy', mm_cfg.Radio,
                           # choices
                           (_('confirm'),
                            _('require approval'),
                            _('confirm+approval')),
                           1,
                           _('What steps are required for subscription?<br>'),
                           _('''confirm (*) - email confirmation required <br>
                           require approval - require list administrator
                           approval for subscriptions <br>
                           confirm+approval - both confirm and approve
                           
                           <p>(*) when someone requests a subscription,
                           Mailman sends them a notice with a unique
                           subscription request number that they must reply to
                           in order to subscribe.<br> This prevents
                           mischievous (or malicious) people from creating
                           subscriptions for others without their consent.'''))

        # some helpful values
        admin = mlist.GetScriptURL('admin')

        return [
            _("""List access policies, including anti-spam measures, covering
            members and outsiders.  See also the <a
            href="%(admin)s/archive">Archival Options section</a> for separate
            archive-privacy settings."""),

            _('Subscribing'),
            ('advertised', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('''Advertise this list when people ask what lists are on this
             machine?''')),

            sub_cfentry,
            
            _("Membership exposure"),
            ('private_roster', mm_cfg.Radio,
             (_('Anyone'), _('List members'), _('List admin only')), 0,
             _('Who can view subscription list?'),

             _('''When set, the list of subscribers is protected by member or
             admin password authentication.''')),

            ('obscure_addresses', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _("""Show member addrs so they're not directly recognizable as
             email addrs?"""),
             _("""Setting this option causes member email addresses to be
             transformed when they are presented on list web pages (both in
             text and as links), so they're not trivially recognizable as
             email addresses.  The intention is to prevent the addresses
             from being snarfed up by automated web scanners for use by
             spammers.""")),

            _("General posting filters"),
            ('moderated', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _('Must posts be approved by the list moderator?')),

            ('member_posting_only', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _("""Restrict posting privilege to list members?
             (<i>member_posting_only</i>)"""),

             _("""Use this option if you want to restrict posting to list
             members.  If you want list members to be able to post, plus a
             handful of other posters, see the <i> posters </i> setting
             below.""")),

            ('posters', mm_cfg.EmailList, (5, WIDTH), 1,
             _('''Addresses of members accepted for posting to this list
             without implicit approval requirement. (See
             <a href="?VARHELP=privacy/member_posting_only">Restrict... to list
             members)</a> for whether or not this is in addition to allowing
             posting by list members'''),

             _("""Adding entries here will have one of two effects, according
             to whether another option restricts posting to members.

             <ul>
                 <li>If <i>member_posting_only</i> is 'yes', then entries
                 added here will have posting privilege in addition to list
                 members.

                 <li>If <i>member_posting_only</i> is 'no', then <em>only</em>
                 the posters listed here will be able to post without admin
                 approval.

             </ul>""")),

            _("Spam-specific posting filters"),

            ('require_explicit_destination', mm_cfg.Radio,
             (_('No'), _('Yes')), 0,
             _("""Must posts have list named in destination (to, cc) field
             (or be among the acceptable alias names, specified below)?"""),

             _("""Many (in fact, most) spams do not explicitly name their
             myriad destinations in the explicit destination addresses - in
             fact often the To: field has a totally bogus address for
             obfuscation.  The constraint applies only to the stuff in the
             address before the '@' sign, but still catches all such spams.

             <p>The cost is that the list will not accept unhindered any
             postings relayed from other addresses, unless

             <ol>
                 <li>The relaying address has the same name, or

                 <li>The relaying address name is included on the options that
                 specifies acceptable aliases for the list.

             </ol>""")),

            ('acceptable_aliases', mm_cfg.Text, (4, WIDTH), 0,
             _("""Alias names (regexps) which qualify as explicit to or cc
             destination names for this list."""),

             _("""Alternate addresses that are acceptable when
             `require_explicit_destination' is enabled.  This option takes a
             list of regular expressions, one per line, which is matched
             against every recipient address in the message.  The matching is
             performed with Python's re.match() function, meaning they are
             anchored to the start of the string.
             
             <p>For backwards compatibility with Mailman 1.1, if the regexp
             does not contain an `@', then the pattern is matched against just
             the local part of the recipient address.  If that match fails, or
             if the pattern does contain an `@', then the pattern is matched
             against the entire recipient address.
             
             <p>Matching against the local part is deprecated; in a future
             release, the pattern will always be matched against the entire
             recipient address.""")),

            ('max_num_recipients', mm_cfg.Number, 5, 0, 
             _('Ceiling on acceptable number of recipients for a posting.'),

             _('''If a posting has this number, or more, of recipients, it is
             held for admin approval.  Use 0 for no ceiling.''')),

            ('forbidden_posters', mm_cfg.EmailList, (5, WIDTH), 1,
             _('Addresses whose postings are always held for approval.'),
             _('''Email addresses whose posts should always be held for
             approval, no matter what other options you have set.  See also
             the subsequent option which applies to arbitrary content of
             arbitrary headers.''')),

            ('bounce_matching_headers', mm_cfg.Text, (6, WIDTH), 0,
             _('Hold posts with header value matching a specified regexp.'),
             _("""Use this option to prohibit posts according to specific
             header values.  The target value is a regular-expression for
             matching against the specified header.  The match is done
             disregarding letter case.  Lines beginning with '#' are ignored
             as comments.

             <p>For example:<pre>to: .*@public.com </pre> says to hold all
             postings with a <em>To:</em> mail header containing '@public.com'
             anywhere among the addresses.

             <p>Note that leading whitespace is trimmed from the regexp.  This
             can be circumvented in a number of ways, e.g. by escaping or
             bracketing it.
             
             <p> See also the <em>forbidden_posters</em> option for a related
             mechanism.""")),

          ('anonymous_list', mm_cfg.Radio, (_('No'), _('Yes')), 0,
           _("""Hide the sender of a message, replacing it with the list
           address (Removes From, Sender and Reply-To fields)""")),
          ]

