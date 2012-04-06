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

"""Test the header chain."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestHeaderChain',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.chains.headers import HeaderMatchRule
from mailman.config import config
from mailman.email.message import Message
from mailman.interfaces.chain import LinkAction
from mailman.testing.layers import ConfigLayer
from mailman.testing.helpers import LogFileMark, configuration



class TestHeaderChain(unittest.TestCase):
    """Test the header chain code."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        # Python 2.6 does not have assertListEqual().
        self._leq = getattr(self, 'assertListEqual', self.assertEqual)

    @configuration('antispam', header_checks="""
    Foo: a+
    Bar: bb?
    """)
    def test_config_checks(self):
        # Test that the header-match chain has the header checks from the
        # configuration file.
        chain = config.chains['header-match']
        # The links are created dynamically; the rule names will all start
        # with the same prefix, but have a variable suffix.  The actions will
        # all be to jump to the named chain.  Do these checks now, while we
        # collect other useful information.
        post_checks = []
        saw_any_rule = False
        for link in chain.get_links(self._mlist, Message(), {}):
            if link.rule.name == 'any':
                saw_any_rule = True
                self.assertEqual(link.action, LinkAction.jump)
            elif saw_any_rule:
                raise AssertionError("'any' rule was not last")
            else:
                self.assertEqual(link.rule.name[:13], 'header-match-')
                self.assertEqual(link.action, LinkAction.defer)
                post_checks.append((link.rule.header, link.rule.pattern))
        self._leq(post_checks, [
            ('Foo', 'a+'),
            ('Bar', 'bb?'),
            ])

    @configuration('antispam', header_checks="""
    Foo: foo
    A-bad-line
    Bar: bar
    """)
    def test_bad_configuration_line(self):
        # Take a mark on the error log file.
        mark = LogFileMark('mailman.error')
        # A bad value in [antispam]header_checks should just get ignored, but
        # with an error message logged.
        chain = config.chains['header-match']
        # The links are created dynamically; the rule names will all start
        # with the same prefix, but have a variable suffix.  The actions will
        # all be to jump to the named chain.  Do these checks now, while we
        # collect other useful information.
        post_checks = []
        saw_any_rule = False
        for link in chain.get_links(self._mlist, Message(), {}):
            if link.rule.name == 'any':
                saw_any_rule = True
                self.assertEqual(link.action, LinkAction.jump)
            elif saw_any_rule:
                raise AssertionError("'any' rule was not last")
            else:
                self.assertEqual(link.rule.name[:13], 'header-match-')
                self.assertEqual(link.action, LinkAction.defer)
                post_checks.append((link.rule.header, link.rule.pattern))
        self._leq(post_checks, [
            ('Foo', 'foo'),
            ('Bar', 'bar'),
            ])
        # Check the error log.
        self.assertEqual(mark.readline()[-77:-1],
                         'Configuration error: [antispam]header_checks '
                         'contains bogus line: A-bad-line')

    def test_duplicate_header_match_rule(self):
        # 100% coverage: test an assertion in a corner case.
        #
        # Save the existing rules so they can be restored later.
        saved_rules = config.rules.copy()
        next_rule_name = 'header-match-{0:02}'.format(HeaderMatchRule._count)
        config.rules[next_rule_name] = object()
        try:
            self.assertRaises(AssertionError,
                              HeaderMatchRule, 'x-spam-score', '.*')
        finally:
            config.rules = saved_rules
