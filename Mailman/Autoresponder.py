# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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
        # this value can be
        #  0 - no autoresponse on the -request line
        #  1 - autorespond, but discard the original message
        #  2 - autorespond, and forward the message on to be processed
        self.autorespond_requests = 0
        self.autoresponse_postings_text = ''
        self.autoresponse_admin_text = ''
        self.autoresponse_request_text = ''
        self.autoresponse_graceperiod = 90 # days
        # non-configurable
        self.postings_responses = {}
        self.admin_responses = {}
        self.request_responses = {}

    def GetConfigInfo(self):
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            """Auto-responder characteristics.<p>

In the text fields below, Python %(string)s interpolation is performed with
the following key/value substitutions:
<p><ul>
    <li><b>%(listname)s</b> - <em>gets the name of the mailing list</em>
    <li><b>%(listurl)s</b> - <em>gets the list's listinfo URL</em>
    <li><b>%(requestemail)s</b> - <em>gets the list's -request address</em>
    <li><b>%(adminemail)s</b> - <em>gets the list's -admin address</em>
</ul>

<p>For each text field, you can either enter the text directly into the text
box, or you can specify a file on your local system to upload as the text.""",

            ('autorespond_postings', mm_cfg.Toggle, ('No', 'Yes'), 0,
             'Should Mailman send an auto-response to mailing list posters?'),

            ('autoresponse_postings_text', mm_cfg.FileUpload,
             (6, WIDTH), 0,
             'Auto-response text to send to mailing list posters.'),

            ('autorespond_admin', mm_cfg.Toggle, ('No', 'Yes'), 0,
             '''Should Mailman send an auto-response to emails sent to the
-admin address?'''),

            ('autoresponse_admin_text', mm_cfg.FileUpload,
             (6, WIDTH), 0,
             'Auto-response text to send to -admin emails.'),

            ('autorespond_requests', mm_cfg.Radio,
             ('No', 'Yes, w/discard', 'Yes, w/forward'), 0,
             '''Should Mailman send an auto-response to emails sent to the
-request address?  If you choose yes, decide whether you want Mailman to
discard the original email, or forward it on to the system as a normal mail
command.'''),

            ('autoresponse_request_text', mm_cfg.FileUpload,
             (6, WIDTH), 0,
             'Auto-response text to send to -request emails.'),

            ('autoresponse_graceperiod', mm_cfg.Number, 3, 0,
             '''Number of days between auto-responses to either the mailing
list or -admin address from the same poster.  Set to zero (or negative) for
no grace period (i.e. auto-respond to every message).'''),

            ]
