# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Set up testing.

This is used as an interface to buildout.cfg's [test] section.
zope.testrunner supports an initialization variable.  It is set to import and
run the following test initialization method.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'initialize',
    ]



def initialize(root_directory):
    """Initialize the test infrastructure."""
    from mailman.testing import layers
    layers.MockAndMonkeyLayer.testing_mode = True
    layers.ConfigLayer.enable_stderr();
    layers.ConfigLayer.set_root_directory(root_directory)
