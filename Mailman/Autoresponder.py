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

"""MailList mixin class managing the autoresponder.
"""

from Mailman import mm_cfg



class Autoresponder:
    def InitVars(self):
        # configurable
        self.autorespond_postings = 0
        self.autorespond_admin = 0
        self.autoresponse_postings_text = ''
        self.autoresponse_admin_text = ''
        self.autoresponse_graceperiod = 90 # days
        # non-configurable
        self.postings_responses = {}
        self.admin_responses = {}

    def GetConfigInfo(self):
        return [
            'Auto-responder characteristics.',

            ('autorespond_postings', mm_cfg.Toggle, ('No', 'Yes'), 0,
             'Should Mailman send an auto-response to mailing list posters?'),

            ('autoresponse_postings_text', mm_cfg.Text, ('6', '30'), 0,
             """Auto-response text to send to mailing list posters.
Python %(string)s interpolation is performed on the text with the following
key/value pairs.<p>
<b>listname</b> <em>gets the name of the mailing list</em><br>
<b>listurl</b> <em>gets the list's listinfo URL</em><br>
<b>requestemail</b> <em>gets the list's -request address</em><br>
<b>adminemail</b> <em>gets the list's -admin address</em>"""),

            ('autorespond_admin', mm_cfg.Toggle, ('No', 'Yes'), 0,
             'Should Mailman send an auto-response to emails sent to the '
             '-admin address?'),

            ('autoresponse_admin_text', mm_cfg.Text, ('6', '30'), 0,
             """Auto-response text to send to -admin emails.
Python %(string)s interpolation is performed on the text with the following
key/value pairs.<p>
<b>listname</b> <em>gets the name of the mailing list</em><br>
<b>listurl</b> <em>gets the list's listinfo URL</em><br>
<b>requestemail</b> <em>gets the list's -request address</em><br>
<b>adminemail</b> <em>gets the list's -admin address</em>"""),

            ('autoresponse_graceperiod', mm_cfg.Number, 3, 0,
             '''Number of days between auto-responses to either the mailing
list or -admin address from the same poster.  Set to zero (or negative) for
no grace period (i.e. auto-respond to every message).'''),

            ]
