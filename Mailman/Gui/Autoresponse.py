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

"""Administrative GUI for the autoresponder."""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.i18n import _

BADJOINER = '</code>, <code>'



class Autoresponse:
    def GetConfigCategory(self):
        return 'autoreply', _('Auto-responder')

    def GetConfigInfo(self, mlist, category, subcat=None):
        if category <> 'autoreply':
            return None
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            _("""\
Auto-responder characteristics.<p>

In the text fields below, string interpolation is performed with
the following key/value substitutions:
<p><ul>
    <li><b>listname</b> - <em>gets the name of the mailing list</em>
    <li><b>listurl</b> - <em>gets the list's listinfo URL</em>
    <li><b>requestemail</b> - <em>gets the list's -request address</em>
    <li><b>adminemail</b> - <em>gets the list's -admin address</em>
    <li><b>owneremail</b> - <em>gets the list's -owner address</em>
</ul>

<p>For each text field, you can either enter the text directly into the text
box, or you can specify a file on your local system to upload as the text."""),

            ('autorespond_postings', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('''Should Mailman send an auto-response to mailing list
             posters?''')),

            ('autoresponse_postings_text', mm_cfg.FileUpload,
             (6, WIDTH), 0,
             _('Auto-response text to send to mailing list posters.')),

            ('autorespond_admin', mm_cfg.Toggle, (_('No'), _('Yes')), 0,
             _('''Should Mailman send an auto-response to emails sent to the
             -admin and -owner addresses?''')),

            ('autoresponse_admin_text', mm_cfg.FileUpload,
             (6, WIDTH), 0,
             _('Auto-response text to send to -admin and -owner emails.')),

            ('autorespond_requests', mm_cfg.Radio,
             (_('No'), _('Yes, w/discard'), _('Yes, w/forward')), 0,
             _('''Should Mailman send an auto-response to emails sent to the
             -request address?  If you choose yes, decide whether you want
             Mailman to discard the original email, or forward it on to the
             system as a normal mail command.''')),

            ('autoresponse_request_text', mm_cfg.FileUpload,
             (6, WIDTH), 0,
             _('Auto-response text to send to -request emails.')),

            ('autoresponse_graceperiod', mm_cfg.Number, 3, 0,
             _('''Number of days between auto-responses to either the mailing
             list or -admin/-owner address from the same poster.  Set to zero
             (or negative) for no grace period (i.e. auto-respond to every
             message).''')),
            ]

    def HandleForm(self, mlist, cgidata, doc):
        # BAW: Refactor w/ similar code in NonDigest.py and Digest.py
        for attr in ('autoresponse_postings_text', 'autoresponse_admin_text',
                     'autoresponse_request_text'):
            newval = cgidata.getvalue(attr)
            # Are we converted to using $-strings?
            dollarp = getattr(mlist, 'use_dollar_strings', 0)
            if dollarp:
                ids = Utils.dollar_identifiers(newval)
            else:
                # %-strings
                ids = Utils.percent_identifiers(newval)
            # Here's the list of allowable interpolations
            for allowed in ['listname', 'listurl', 'requestemail',
                            'adminemail', 'owneremail']:
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
