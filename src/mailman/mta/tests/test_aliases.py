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

"""Test the template generating utility."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from cStringIO import StringIO
from zope.component import getUtility

from mailman.app.lifecycle import create_list
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

    def test_duck_typed_aliases(self):
        # Test the .aliases() method with duck typed arguments.
        class Duck:
            def __init__(self, list_name, mail_host):
                self.list_name = list_name
                self.mail_host = mail_host
                self.posting_address = '{0}@{1}'.format(list_name, mail_host)
        duck_list = Duck('sample', 'example.net')
        aliases = list(self.utility.aliases(duck_list))
        self.assertEqual(aliases, [
            'sample@example.net',
            'sample-bounces@example.net',
            'sample-confirm@example.net',
            'sample-join@example.net',
            'sample-leave@example.net',
            'sample-owner@example.net',
            'sample-request@example.net',
            'sample-subscribe@example.net',
            'sample-unsubscribe@example.net',
            ])

    def test_duck_typed_destinations(self):
        # Test the .destinations() method with duck typed arguments.
        class Duck:
            def __init__(self, list_name):
                self.list_name = list_name
        duck_list = Duck('sample')
        destinations = list(self.utility.destinations(duck_list))
        self.assertEqual(destinations, [
            'sample',
            'sample-bounces',
            'sample-confirm',
            'sample-join',
            'sample-leave',
            'sample-owner',
            'sample-request',
            'sample-subscribe',
            'sample-unsubscribe',
            ])



class TestPostfix(unittest.TestCase):
    """Test the Postfix LMTP alias generator."""

    layer = ConfigLayer

    def setUp(self):
        self.utility = getUtility(IMailTransportAgentAliases)
        self.mlist = create_list('test@example.com')
        self.output = StringIO()
        self.postfix = LMTP()
        # Python 2.7 has assertMultiLineEqual.  Let this work without bounds.
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)

    def test_aliases(self):
        # Test the format of the Postfix alias generator.
        self.postfix.regenerate(self.output)
        # Strip out the variable and unimportant bits of the output.
        lines = self.output.getvalue().splitlines()
        output = NL.join(lines[7:])
        self.eq(output, """\
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

    def test_two_lists(self):
        # Both lists need to show up in the aliases file.  LP: #874929.
        # Create a second list.
        create_list('other@example.com')
        self.postfix.regenerate(self.output)
        # Strip out the variable and unimportant bits of the output.
        lines = self.output.getvalue().splitlines()
        output = NL.join(lines[7:])
        self.eq(output, """\
# Aliases which are visible only in the @example.com domain.
other@example.com               lmtp:[127.0.0.1]:9024
other-bounces@example.com       lmtp:[127.0.0.1]:9024
other-confirm@example.com       lmtp:[127.0.0.1]:9024
other-join@example.com          lmtp:[127.0.0.1]:9024
other-leave@example.com         lmtp:[127.0.0.1]:9024
other-owner@example.com         lmtp:[127.0.0.1]:9024
other-request@example.com       lmtp:[127.0.0.1]:9024
other-subscribe@example.com     lmtp:[127.0.0.1]:9024
other-unsubscribe@example.com   lmtp:[127.0.0.1]:9024

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
