# Copyright (C) 2002 by the Free Software Foundation, Inc.
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

"""GUI component managing the content filtering options.
"""

from Mailman import mm_cfg
from Mailman.i18n import _
from Mailman.Gui.GUIBase import GUIBase

NL = '\n'



class ContentFilter(GUIBase):
    def GetConfigCategory(self):
        return 'contentfilter', _('Content&nbsp;filtering')

    def GetConfigInfo(self, mlist, category, subcat=None):
        if category <> 'contentfilter':
            return None
        WIDTH = mm_cfg.TEXTFIELDWIDTH

        return [
            _("""Policies concerning concerning the content of list traffic.

            <p>Content filtering works like this: when a message is
            received by the list and you have enabled content filtering, the
            individual attachments are first compared to the
            <a href="?VARHELP=contentfilter/filter_mime_types">filter
            types</a>.  If the attachment type matches an entry in the filter
            types, it is discarded.

            <p>Then, if there are <a
            href="?VARHELP=contentfilter/pass_mime_types">pass types</a>
            defined, any attachment type that does <em>not</em> match a
            pass type is also discarded.  If there are no pass types defined,
            this check is skipped.

            <p>After this initial filtering, any <tt>multipart</tt>
            attachments that are empty are removed.  If the outer message is
            left empty after this filtering, then the whole message is
            discarded.  Then, each <tt>multipart/alternative</tt> section will
            be replaced by just the first alternative that is non-empty after
            filtering.

            <p>Finally, any <tt>text/html</tt> parts that are left in the
            message may be converted to <tt>text/plain</tt> if
            <a href="?VARHELP=contentfilter/convert_html_to_plaintext"</a> is
            enabled and the site is configured to allow these conversions."""),

            ('filter_content', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _("""Should Mailman filter the content of list traffic according
             to the settings below?""")),

            ('filter_mime_types', mm_cfg.Text, (10, WIDTH), 0,
             _("""Remove message attachments that have a matching content
             type."""),
             
             _("""Use this option to remove each message attachment that
             matches one of these content types.  Each line should contain a
             string naming a MIME <tt>type/subtype</tt>,
             e.g. <tt>image/gif</tt>.  Leave off the subtype to remove all
             parts with a matching major content type, e.g. <tt>image</tt>.

             <p>Blank lines are ignored.""")),

            ('pass_mime_types', mm_cfg.Text, (10, WIDTH), 0,
             _("""Remove message attachments that don't have a matching
             content type.  Leave this field blank to skip this filter
             test."""),

             _("""Use this option to remove each message attachment that does
             not have a matching content type.  Requirements and formats are
             exactly like <a href="?VARHELP=contentfilter/filter_mime_types"
             >filter_mime_types</a>.""")),

            ('convert_html_to_plaintext',
             mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _("""Should Mailman convert <tt>text/html</tt> parts to plain
             text?  This conversion happens after MIME attachments have been
             stripped.""")),
            ]

    def _setValue(self, mlist, property, val, doc):
        if property in ('filter_mime_types', 'pass_mime_types'):
            types = []
            for spectype in [s.strip() for s in val.splitlines()]:
                if 0 > spectype.count('/') > 1:
                    doc.addError(_('Bad MIME type ignored: %(spectype)s'))
                else:
                    types.append(spectype.strip().lower())
	    if property == 'filter_mime_types':
                mlist.filter_mime_types = types
	    elif property == 'pass_mime_types':
                mlist.pass_mime_types = types
        else:
            GUIBase._setValue(self, mlist, property, val, doc)

    def getValue(self, mlist, kind, property, params):
        if property == 'filter_mime_types':
            return NL.join(mlist.filter_mime_types)
        if property == 'pass_mime_types':
            return NL.join(mlist.pass_mime_types)
        return None
