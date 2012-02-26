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

"""Test the `confirm` command."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from datetime import datetime
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.registrar import IRegistrar
from mailman.interfaces.usermanager import IUserManager
from mailman.runners.command import CommandRunner
from mailman.testing.helpers import (
    make_testable_runner,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestConfirm(unittest.TestCase):
    """Test confirmations."""

    layer = ConfigLayer

    def setUp(self):
        # Register a subscription requiring confirmation.
        registrar = getUtility(IRegistrar)
        self._mlist = create_list('test@example.com')
        self._token = registrar.register(self._mlist, 'anne@example.org')
        self._commandq = config.switchboards['command']
        self._runner = make_testable_runner(CommandRunner, 'command')
        config.db.commit()

    def test_confirm_with_re_prefix(self):
        subject = 'Re: confirm {0}'.format(self._token)
        msg = mfs("""\
From: anne@example.org
To: test-confirm@example.com

""")
        msg['Subject'] = subject
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        # Anne is now a confirmed member so her user record and email address
        # should exist in the database.
        manager = getUtility(IUserManager)
        user = manager.get_user('anne@example.org')
        address = list(user.addresses)[0]
        self.assertEqual(address.email, 'anne@example.org')
        self.assertEqual(address.verified_on, datetime(2005, 8, 1, 7, 49, 23))
        address = manager.get_address('anne@example.org')
        self.assertEqual(address.email, 'anne@example.org')

    def test_confirm_with_random_ascii_prefix(self):
        subject = '\x99AW: confirm {0}'.format(self._token)
        msg = mfs("""\
From: anne@example.org
To: test-confirm@example.com

""")
        msg['Subject'] = subject
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        # Anne is now a confirmed member so her user record and email address
        # should exist in the database.
        manager = getUtility(IUserManager)
        user = manager.get_user('anne@example.org')
        address = list(user.addresses)[0]
        self.assertEqual(address.email, 'anne@example.org')
        self.assertEqual(address.verified_on, datetime(2005, 8, 1, 7, 49, 23))
        address = manager.get_address('anne@example.org')
        self.assertEqual(address.email, 'anne@example.org')
