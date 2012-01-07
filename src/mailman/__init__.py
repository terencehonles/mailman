# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""The `mailman` package."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import os
import sys


# This is a namespace package.
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)


# We have to initialize the i18n subsystem before anything else happens,
# however, we'll initialize it differently for tests.  We have to do it this
# early so that module contents is set up before anything that needs it is
# imported.
#
# Do *not* do this if we're building the documentation.
if 'build_sphinx' not in sys.argv:
    if sys.argv[0].split(os.sep)[-1] == 'test':
        from mailman.testing.i18n import initialize
    else:
        from mailman.core.i18n import initialize
    initialize()
