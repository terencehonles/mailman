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



_translation = gettext.NullTranslations()

def set_language(language):
    global _translation
    try:
        _translation = gettext.translation('mailman', mm_cfg.MESSAGES_DIR,
                                           [language])
    except IOError:
        # The selected language was not installed in messages, so fall back to
        # untranslated English.
        _translation = gettext.NullTranslations()


def _x(s, frame):
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
    # A `safe' dictionary is used so we won't get an exception if there's a
    # missing key in the dictionary.
    dict = SafeDict(frame.f_globals.copy())
    dict.update(frame.f_locals)
    # Translate the string, then interpolate into it.
    return _translation.gettext(s) % dict
    


# Public version, to be used by most modules.  There are three ways to get the
# stack frame to serve as the namespace source.  First, we try to use the
# Python 2.1 extension to the sys module.  If that's not there, we fall back
# to the optional Mailman enhancement module, and finally use the
# tried-and-true (but slow) pure Python approach.  The latter should work in
# every supported version of Python.
if hasattr(sys, '_getframe'):
    def _(s):
        return _x(s, sys._getframe(1))
else:
    try:
        import _mailman
        def _(s):
            return _x(s, _mailman._getframe(1))
    except ImportError:
        def _(s):
            exc = 'exc'
            try: raise exc
            except exc:
                # Get one frame up the stack.
                frame = sys.exc_info()[2].tb_frame.f_back
            return _x(s, frame)
