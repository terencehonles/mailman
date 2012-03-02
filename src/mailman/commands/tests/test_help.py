# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Additional tests for the `help` email command."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.commands.eml_help import Help
from mailman.email.message import Message
from mailman.interfaces.command import ContinueProcessing
from mailman.runners.command import Results
from mailman.testing.layers import ConfigLayer



class TestHelp(unittest.TestCase):
    """Test email help."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._help = Help()

    def test_too_many_arguments(self):
        # Error message when too many help arguments are given.
        results = Results()
        status = self._help.process(self._mlist, Message(), {}, 
                                    ('more', 'than', 'one'),
                                    results)
        self.assertEqual(status, ContinueProcessing.no)
        self.assertEqual(unicode(results), """\
The results of your email command are provided below.

help: too many arguments: more than one
""")

    def test_no_such_command(self):
        # Error message when asking for help on an existent command.
        results = Results()
        status = self._help.process(self._mlist, Message(), {}, 
                                    ('doesnotexist',), results)
        self.assertEqual(status, ContinueProcessing.no)
        self.assertEqual(unicode(results), """\
The results of your email command are provided below.

help: no such command: doesnotexist
""")
