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

"""Test `bin/mailman create`."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import sys
import unittest

from mailman.app.lifecycle import create_list
from mailman.commands.cli_lists import Create
from mailman.testing.layers import ConfigLayer



class FakeArgs:
    language = None
    owners = []
    quiet = False
    domain = None
    listname = None
    notify = False


class FakeParser:
    def __init__(self):
        self.message = None

    def error(self, message):
        self.message = message
        sys.exit(1)



class TestCreate(unittest.TestCase):
    """Test `bin/mailman create`."""

    layer = ConfigLayer

    def setUp(self):
        self.command = Create()
        self.command.parser = FakeParser()
        self.args = FakeArgs()

    def test_cannot_create_duplicate_list(self):
        # Cannot create a mailing list if it already exists.
        create_list('test@example.com')
        self.args.listname = ['test@example.com']
        try:
            self.command.process(self.args)
        except SystemExit:
            pass
        self.assertEqual(self.command.parser.message,
                         'List already exists: test@example.com')

    def test_invalid_posting_address(self):
        # Cannot create a mailing list with an invalid posting address.
        self.args.listname = ['foo']
        try:
            self.command.process(self.args)
        except SystemExit:
            pass
        self.assertEqual(self.command.parser.message,
                         'Illegal list name: foo')

    def test_invalid_owner_addresses(self):
        # Cannot create a list with invalid owner addresses.  LP: #778687
        self.args.listname = ['test@example.com']
        self.args.domain = True
        self.args.owners = ['main=True']
        try:
            self.command.process(self.args)
        except SystemExit:
            pass
        self.assertEqual(self.command.parser.message,
                         'Illegal owner addresses: main=True')
