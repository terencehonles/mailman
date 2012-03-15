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

"""Test notifications."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import os
import shutil
import tempfile
import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.app.membership import add_member
from mailman.app.notifications import send_welcome_message
from mailman.config import config
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.member import DeliveryMode
from mailman.testing.helpers import get_queue_messages
from mailman.testing.layers import ConfigLayer



class TestNotifications(unittest.TestCase):
    """Test notifications."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.welcome_message_uri = 'mailman:///welcome.txt'
        self._mlist.display_name = 'Test List'
        self.var_dir = tempfile.mkdtemp()
        config.push('template config', """\
        [paths.testing]
        template_dir: {0}/templates
        """.format(self.var_dir))
        # Populate the template directories with a few fake templates.
        path = os.path.join(self.var_dir, 'templates', 'site', 'en')
        os.makedirs(path)
        with open(os.path.join(path, 'welcome.txt'), 'w') as fp:
            print("""\
Welcome to the $list_name mailing list.

    Posting address: $fqdn_listname
    Help and other requests: $list_requests
    Your name: $user_name
    Your address: $user_address
    Your options: $user_options_uri""", file=fp)
        # Write a list-specific welcome message.
        path = os.path.join(self.var_dir, 'templates', 'lists',
                            'test@example.com', 'xx')
        os.makedirs(path)
        with open(os.path.join(path, 'welcome.txt'), 'w') as fp:
            print('You just joined the $list_name mailing list!', file=fp)
        # Python 2.7 has assertMultiLineEqual.  Let this work without bounds.
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)

    def tearDown(self):
        config.pop('template config')
        shutil.rmtree(self.var_dir)

    def test_welcome_message(self):
        en = getUtility(ILanguageManager).get('en')
        add_member(self._mlist, 'anne@example.com', 'Anne Person',
                   'password', DeliveryMode.regular, 'en')
        send_welcome_message(self._mlist, 'anne@example.com', en,
                             DeliveryMode.regular)
        # Now there's one message in the virgin queue.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        message = messages[0].msg
        self.assertEqual(str(message['subject']),
                         'Welcome to the "Test List" mailing list')
        self.eq(message.get_payload(), """\
Welcome to the Test List mailing list.

    Posting address: test@example.com
    Help and other requests: test-request@example.com
    Your name: Anne Person
    Your address: anne@example.com
    Your options: http://example.com/anne@example.com
""")

    def test_more_specific_welcome_message_nonenglish(self):
        # mlist.welcome_message_uri can contain placeholders for the fqdn list
        # name and language.
        self._mlist.welcome_message_uri = (
            'mailman:///$listname/$language/welcome.txt')
        # Add the xx language and subscribe Anne using it.
        manager = getUtility(ILanguageManager)
        xx = manager.add('xx', 'us-ascii', 'Xlandia')
        add_member(self._mlist, 'anne@example.com', 'Anne Person',
                   'password', DeliveryMode.regular, 'xx')
        send_welcome_message(self._mlist, 'anne@example.com', xx,
                             DeliveryMode.regular)
        # Now there's one message in the virgin queue.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        message = messages[0].msg
        self.assertEqual(str(message['subject']),
                         'Welcome to the "Test List" mailing list')
        self.assertEqual(message.get_payload(),
                         'You just joined the Test List mailing list!')
