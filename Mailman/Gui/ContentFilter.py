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
            _('Policies concerning concerning the content of list traffic.'),

            ('filter_content', mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _("""Should Mailman filter the content of list traffic according
             to the settings below?""")),

            ('filter_mime_types', mm_cfg.Text, (10, WIDTH), 0,
             _("""Remove sections of messages that have a matching MIME
             type."""),
             
             _("""Use this option to remove each message section with a
             matching MIME type.  Each line should contain a string naming a
             MIME <tt>type/subtype</tt>, e.g. <tt>image/gif</tt>.  Leave off
             the subtype to remove all parts with a matching MIME major type,
             e.g. <tt>image</tt>.  Blank lines are ignored.

             <p>After stripping message parts, any <tt>multipart</tt>
             attachment that is empty as a result is removed all together.  If
             the outer part's MIME type matches one of the strip types, or if
             all of the outer part's subparts are stripped, then the whole
             message is discarded.  Finally, each
             <tt>multipart/alternative</tt> section will be replaced by just
             the first alternative that is non-empty after the specified types
             have been removed.""")),

            ('convert_html_to_plaintext',
             mm_cfg.Radio, (_('No'), _('Yes')), 0,
             _("""Should Mailman convert <tt>text/html</tt> parts to plain
             text?  This conversion happens after MIME attachments have been
             stripped.""")),
            ]

    def _setValue(self, mlist, property, val, doc):
        if property == 'filter_mime_types':
            types = []
            for spectype in val.splitlines():
                if 0 > spectype.count('/') > 1:
                    doc.addError(_('Bad MIME type ignored: %(spectype)s'))
                else:
                    types.append(spectype.strip().lower())
            mlist.filter_mime_types = types
        else:
            GUIBase._setValue(self, mlist, property, val, doc)

    def getValue(self, mlist, kind, property, params):
        if property == 'filter_mime_types':
            return NL.join(mlist.filter_mime_types)
        return None
