# Copyright (C) 2001,2002 by the Free Software Foundation, Inc.
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

"""GUI component for managing the non-digest delivery options.
"""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.i18n import _

BADJOINER = '</code>, <code>'



class NonDigest:
    def GetConfigCategory(self):
        return 'nondigest', _('Non-digest&nbsp;options')

    def GetConfigInfo(self, mlist, category, subcat=None):
        if category <> 'nondigest':
            return None
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        info = [
            _("Policies concerning immediately delivered list traffic."),

            ('nondigestable', mm_cfg.Toggle, (_('No'), _('Yes')), 1,
             _("""Can subscribers choose to receive mail immediately, rather
             than in batched digests?""")),

            ('msg_header', mm_cfg.Text, (10, WIDTH), 0,
             _('Header added to mail sent to regular list members'),
             _('''Text prepended to the top of every immediately-delivery
             message. ''') + Utils.maketext('headfoot.html',
                                            mlist=mlist, raw=1)),
            
            ('msg_footer', mm_cfg.Text, (10, WIDTH), 0,
             _('Footer added to mail sent to regular list members'),
             _('''Text appended to the bottom of every immediately-delivery
             message. ''') + Utils.maketext('headfoot.html',
                                            mlist=mlist, raw=1)),
            ]

        if mm_cfg.OWNERS_CAN_ENABLE_PERSONALIZATION:
            info.extend([
                ('personalize', mm_cfg.Toggle, (_('No'), _('Yes')), 1,

                 _('''Should Mailman personalize each non-digest delivery?
                 This is often useful for announce-only lists, but <a
                 href="?VARHELP=nondigest/personalize">read the details</a>
                 section for a discussion of important performance
                 issues.'''),

                 _("""Normally, Mailman sends the regular delivery messages to
                 the mail server in batches.  This is much more efficent
                 because it reduces the amount of traffic between Mailman and
                 the mail server.

                 <p>However, some lists can benefit from a more personalized
                 approach.  In this case, Mailman crafts a new message for
                 each member on the regular delivery list.  Turning this
                 feature on may degrade the performance of your site, so you
                 need to carefully consider whether the trade-off is worth it,
                 or whether there are other ways to accomplish what you want.
                 You should also carefully monitor your system load to make
                 sure it is acceptable.

                 <p>When personalized lists are enabled, two things happen.
                 First, the <code>To:</code> header of the posted message is
                 modified so that each individual user is addressed
                 specifically.  I.e. it looks like the message was addressed
                 to the recipient instead of to the list.

                 <p>Second a few more expansion variables that can be included
                 in the <a href="?VARHELP=nondigest/msg_header">message
                 header</a> and
                 <a href="?VARHELP=nondigest/msg_footer">message footer</a>.

                 <p>These additional substitution variables will be available
                 for your headers and footers, when this feature is enabled:

                 <ul><li><b>user_address</b> - The address of the user,
                         coerced to lower case.
                     <li><b>user_delivered_to</b> - The case-preserved address
                         that the user is subscribed with.
                     <li><b>user_password</b> - The user's password.
                     <li><b>user_name</b> - The user's full name.
                     <li><b>user_optionsurl</b> - The url to the user's option
                         page.
                 </ul>
                 """))
                ])

        return info

    def HandleForm(self, mlist, cgidata, doc):
        for attr in ('msg_header', 'msg_footer'):
            handle_form(mlist, attr, cgidata, doc, 1)



# This is code that can be shared between the digest and non-digest headers
# and footers.
def handle_form(mlist, attr, cgidata, doc, allow_personalizations):
    newval = cgidata.getvalue(attr)
    # Are we converted to using $-strings?
    dollarp = getattr(mlist, 'use_dollar_strings', 0)
    if dollarp:
        ids = Utils.dollar_identifiers(newval)
    else:
        # %-strings
        ids = Utils.percent_identifiers(newval)
    # Here's the list of allowable interpolations
    allows = ['real_name', 'list_name', 'host_name', 'web_page_url',
              'description', 'info', 'cgiext', '_internal_name']
    if allow_personalizations and mlist.personalize:
        allows.extend(['user_address', 'user_delivered_to',
                       'user_password', 'user_name',
                       'user_optionsurl'])
    for allowed in allows:
        if ids.has_key(allowed):
            del ids[allowed]
    if ids:
        # What's left are not allowed
        badkeys = ids.keys()
        badkeys.sort()
        bad = BADJOINER.join(badkeys)
        doc.addError(_(
            """The following illegal interpolation variables were
            found in the <code>%(attr)s</code> string:
            <code>%(bad)s</code>
            <p>Your changes will be discarded.  Please correct the
            mistakes and try again."""),
                     tag=_('Error: '))
        return
    # Now if we're still using %-strings, do a roundtrip conversion
    # and see if the converted value is the same as the new value.  If
    # not, then they probably left off a trailing `s'.  We'll warn
    # them and use the corrected string.
    if not dollarp:
        fixed = Utils.to_percent(Utils.to_dollar(newval))
        if fixed <> newval:
            doc.addError(_(
                """Your <code>%(attr)s</code> string appeared to have
                some correctable problems in its new value.  The fixed
                value will be used instead.  Please double check that
                this is what you intended.
                """))
            newval = fixed
    setattr(mlist, attr, newval)
