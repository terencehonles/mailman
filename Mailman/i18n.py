# Copyright (C) 2000,2001 by the Free Software Foundation, Inc.
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

import sys
import gettext

from Mailman import mm_cfg
from Mailman.SafeDict import SafeDict

_translation = None



def set_language(language=None):
    global _translation
    if language is not None:
        language = [language]
    try:
        _translation = gettext.translation('mailman', mm_cfg.MESSAGES_DIR,
                                           language)
    except IOError:
        # The selected language was not installed in messages, so fall back to
        # untranslated English.
        _translation = gettext.NullTranslations()

def get_translation():
    return _translation

def set_translation(translation):
    global _translation
    _translation = translation


# Set up the global translation based on environment variables.  Mostly used
# for command line scripts.
if _translation is None:
    set_language()



def _(s):
    # Do translation of the given string into the current language, and do
    # Ping-string interpolation into the resulting string.
    #
    # This lets you write something like:
    #
    #     now = time.ctime(time.time())
    #     print _('The current time is: %(now)s')
    #
    # and have it Just Work.  Note that the lookup order for keys in the
    # original string is 1) locals dictionary, 2) globals dictionary.
    #
    # First, get the frame of the caller
    frame = sys._getframe(1)
    # A `safe' dictionary is used so we won't get an exception if there's a
    # missing key in the dictionary.
    dict = SafeDict(frame.f_globals.copy())
    dict.update(frame.f_locals)
    # Translate the string, then interpolate into it.
    return _translation.gettext(s) % dict
