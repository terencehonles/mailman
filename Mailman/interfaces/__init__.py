# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

import os
import sys

from munepy import Enum
from zope.interface import implementedBy
from zope.interface.interfaces import IInterface

__all__ = [
    'Action',
    'NewsModeration',
    ]



def _populate():
    import Mailman.interfaces
    iface_mod = sys.modules['Mailman.interfaces']
    # Expose interfaces defined in sub-modules into the top-level package
    for filename in os.listdir(os.path.dirname(iface_mod.__file__)):
        base, ext = os.path.splitext(filename)
        if ext <> '.py':
            continue
        modname = 'Mailman.interfaces.' + base
        __import__(modname)
        module = sys.modules[modname]
        for name in dir(module):
            obj = getattr(module, name)
            try:
                is_enum = issubclass(obj, Enum)
            except TypeError:
                is_enum = False
            if IInterface.providedBy(obj) or is_enum:
                setattr(iface_mod, name, obj)
                __all__.append(name)


_populate()



class Action(Enum):
    hold    = 0
    reject  = 1
    discard = 2
    accept  = 3
    defer   = 4



class NewsModeration(Enum):
    # The newsgroup is not moderated
    none = 0
    # The newsgroup is moderated, but allows for an open posting policy.
    open_moderated = 1
    # The newsgroup is moderated
    moderated = 2
