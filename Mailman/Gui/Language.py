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

"""MailList mixin class managing the language options.
"""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog



class Language:
    def GetConfigCategory(self):
        return 'language', _('Language&nbsp;options')

    def GetConfigInfo(self, mlist, category, subcat=None):
        if category <> 'language':
            return None
        # Set things up for the language choices
        langs = mlist.GetAvailableLanguages()
        langnames = [_(Utils.GetLanguageDescr(L)) for L in langs]
        try:
            langi = langs.index(mlist.preferred_language)
        except ValueError:
            # Someone must have deleted the list's preferred language.  Could
            # be other trouble lurking!
            langi = 0

        all = Utils.GetDirectories(mm_cfg.TEMPLATE_DIR)
        all.sort()
        checked = [L in langs for L in all]
        allnames = [_(Utils.GetLanguageDescr(L)) for L in all]

        return [
            _('Natural language (internationalization) options.'),

            ('preferred_language', mm_cfg.Select,
             (langs, langnames, langi),
             0,
             _('Default language for this list.'),
             _('''This is the default natural language for this mailing list.
             If <a href="?VARHELP=language/available_languages">more than one
             language</a> is supported then users will be able to select their
             own preferences for when they interact with the list.  All other
             interactions will be conducted in the default language.  This
             applies to both web-based and email-based messages, but not to
             email posted by list members.''')),

            ('available_languages', mm_cfg.Checkbox,
             (allnames, checked, 0, all), 0,
             _('Languages supported by this list.'),

             _('''These are all the natural languages supported by this list.
             Note that the
             <a href="?VARHELP=language/preferred_language">default
             language</a> must be included.''')),

            ]
