# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""Test the template generating utility."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from cStringIO import StringIO
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.mta import IMailTransportAgentAliases
from mailman.mta.postfix import LMTP
from mailman.testing.layers import ConfigLayer

NL = '\n'



class TestAliases(unittest.TestCase):

    layer = ConfigLayer

    def setUp(self):
        self.utility = getUtility(IMailTransportAgentAliases)
        self.mlist = create_list('test@example.com')

    def test_posting_address_first(self):
        # The posting address is always first.
        aliases = list(self.utility.aliases(self.mlist))
        self.assertEqual(aliases[0], self.mlist.posting_address)

    def test_aliases(self):
        # The aliases are the fully qualified email addresses.
        aliases = list(self.utility.aliases(self.mlist))
        self.assertEqual(aliases, [
            'test@example.com',
            'test-bounces@example.com',
            'test-confirm@example.com',
            'test-join@example.com',
            'test-leave@example.com',
            'test-owner@example.com',
            'test-request@example.com',
            'test-subscribe@example.com',
            'test-unsubscribe@example.com',
            ])

    def test_destinations(self):
        # The destinations are just the local part.
        destinations = list(self.utility.destinations(self.mlist))
        self.assertEqual(destinations, [
            'test',
            'test-bounces',
            'test-confirm',
            'test-join',
            'test-leave',
            'test-owner',
            'test-request',
            'test-subscribe',
            'test-unsubscribe',
            ])



class TestPostfix(unittest.TestCase):
    """Test the Postfix LMTP alias generator."""

    layer = ConfigLayer

    def setUp(self):
        self.utility = getUtility(IMailTransportAgentAliases)
        self.mlist = create_list('test@example.com')
        self.output = StringIO()
        self.postfix = LMTP()
        # For Python 2.7's unittest.
        self.maxDiff = None

    def test_aliases(self):
        # Test the format of the Postfix alias generator.
        self.postfix.regenerate(self.output)
        # Python 2.7 has assertMultiLineEqual but Python 2.6 does not.
        eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)
        # Strip out the variable and unimportant bits of the output.
        lines = self.output.getvalue().splitlines()
        output = NL.join(lines[7:])
        eq(output, """\
# Aliases which are visible only in the @example.com domain.
test@example.com               lmtp:[127.0.0.1]:9024
test-bounces@example.com       lmtp:[127.0.0.1]:9024
test-confirm@example.com       lmtp:[127.0.0.1]:9024
test-join@example.com          lmtp:[127.0.0.1]:9024
test-leave@example.com         lmtp:[127.0.0.1]:9024
test-owner@example.com         lmtp:[127.0.0.1]:9024
test-request@example.com       lmtp:[127.0.0.1]:9024
test-subscribe@example.com     lmtp:[127.0.0.1]:9024
test-unsubscribe@example.com   lmtp:[127.0.0.1]:9024
""")



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAliases))
    suite.addTest(unittest.makeSuite(TestPostfix))
    return suite
