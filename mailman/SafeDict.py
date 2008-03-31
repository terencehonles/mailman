# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

from mailman.configuration import config

"""A `safe' dictionary for string interpolation."""

COMMASPACE = ', '

# XXX This module should go away.



class SafeDict(dict):
    """Dictionary which returns a default value for unknown keys.

    This is used in maketext so that editing templates is a bit more robust.
    """
    def __init__(self, d='', charset=None, lang=None):
        super(SafeDict, self).__init__(d)
        if charset:
            self.cset = charset
        elif lang:
            self.cset = config.languages.get_charset(lang)
        else:
            self.cset = 'us-ascii'

    def __getitem__(self, key):
        try:
            return super(SafeDict, self).__getitem__(key)
        except KeyError:
            if isinstance(key, basestring):
                return '%('+key+')s'
            else:
                return '<Missing key: %s>' % `key`

    def interpolate(self, template):
        for k, v in self.items():
            if isinstance(v, str):
                self.__setitem__(k, unicode(v, self.cset))
        return template % self
