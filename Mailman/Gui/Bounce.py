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

from Mailman import mm_cfg
from Mailman.i18n import _
from Mailman.mm_cfg import days



class Bounce:
    def GetConfigCategory(self):
        return 'bounce', _('Bounce detection')

    def GetConfigInfo(self, mlist, category, subcat=None):
        if category <> 'bounce':
            return None
        return [
            _("""These policies control the automatic bounce processing system
            in Mailman.  Here's an overview of how it works.

            <p>When a bounce is received, Mailman tries to extract two pieces
            of information from the message: the address of the member the
            message was intended for, and the severity of the problem causing
            the bounce.  The severity can be either <em>hard</em> or
            <em>soft</em> meaning either a fatal error occurred, or a
            transient error occurred.  When in doubt, a hard severity is used.

            <p>If no member address can be extracted from the bounce, then the
            bounce is usually discarded.  Otherwise, each member is assigned a
            <em>bounce score</em> and every time we encounter a bounce from
            this member we increment the score.  Hard bounces increment by 1
            while soft bounces increment by 0.5.  We only increment the bounce
            score once per day, so even if we receive ten hard bounces from a
            member per day, their score will increase by only 1 for that day.

            <p>When a member's bounce score is greater than the
            <a href="?VARHELP=bounce/bounce_score_threshold">bounce score
            threshold</a>, the subscription is disabled.  Once disabled, the
            member will not receive any postings from the list until their
            membership is explicitly re-enabled (either by the list
            administrator or the user).  However, they will receive occasional
            reminders that their membership has been disabled, and these
            reminders will include information about how to re-enable their
            membership.

            <p>You can control both the
            <a href="?VARHELP=bounce/bounce_you_are_disabled_warnings">number
            of reminders</a> the member will receive and the
            <a href="?VARHELP=bounce/bounce_you_are_disabled_warnings_interval"
            >frequency</a> with which these reminders are sent.

            <p>There is one other important configuration variable; after a
            certain period of time -- during which no bounces from the member
            are received -- the bounce information is
            <a href="?VARHELP=bounce/bounce_info_stale_after">considered
            stale</a> and discarded.  Thus by adjusting this value, and the
            score threshold, you can control how quickly bouncing members are
            disabled.  You should tune both of these to the frequency and
            traffic volume of your list."""),

            ('bounce_processing', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('Should Mailman perform automatic bounce processing?'),
             _("""By setting this value to <em>No</em>, you disable all
             automatic bounce processing for this list, however bounce
             messages will still be discarded so that the list administrator
             isn't inundated with them.""")),

            ('bounce_score_threshold', mm_cfg.Number, 5, 0,
             _("""The maximum member bounce score before the member's
             subscription is disabled.  This value can be a floating point
             number.""")),

            ('bounce_info_stale_after', mm_cfg.Number, 5, 0,
             _("""The number of days after which a member's bounce information
             is discarded, if no new bounces have been received in the
             interim.  This value must be an integer.""")),

            ('bounce_you_are_disabled_warnings', mm_cfg.Number, 5, 0,
             _("""How many <em>Your Membership Is Disabled</em> warnings a
             disabled member should get before their address is removed from
             the mailing list.  Set to 0 to immediately remove an address from
             the list once their bounce score exceeds the threshold.  This
             value must be an integer.""")),

            ('bounce_you_are_disabled_warnings_interval', mm_cfg.Number, 5, 0,
             _("""The number of days between sending the <em>Your Membership
             Is Disabled</em> warnings.  This value must be an integer.""")),
            ]

    def __convert(self, mlist, cgidata, varname, doc, func):
        # BAW: This should really be an attribute on the doc object
        def error(doc, varname, value):
            from Mailman.Cgi.admin import add_error_message
            text = _("""Bad value for <a href="?VARHELP=bounce/%(varname)s"
            >%(varname)s</a>: %(value)s""")
            add_error_message(doc, text, _('Error: '))

        value = cgidata.getvalue(varname)
        if value:
            try:
                setattr(mlist, varname, func(value))
            except ValueError:
                error(doc, varname, value)

    def HandleForm(self, mlist, cgidata, doc):
        def convert(varname, func,
                    self=self, mlist=mlist, cgidata=cgidata, doc=doc):
            self.__convert(mlist, cgidata, varname, doc, func)

        def to_days(value):
            return days(int(value))
        # Do our own form processing so the admin.py script doesn't have to
        # contain all the logic for converting from seconds to days.
        convert('bounce_processing', int)
        convert('bounce_score_threshold', float)
        convert('bounce_info_stale_after', to_days)
        convert('bounce_you_are_disabled_warnings', int)
        convert('bounce_you_are_disabled_warnings_interval', to_days)

    def GetValue(self, mlist, kind, varname, params):
        if varname not in ('bounce_info_stale_after',
                           'bounce_you_are_disabled_warnings_interval'):
            return None
        return int(getattr(mlist, varname) / days(1))
