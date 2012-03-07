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

"""Test the core modification pipelines."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest


from mailman.app.lifecycle import create_list
from mailman.core.pipelines import process
from mailman.testing.helpers import (
    reset_the_world,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestBuiltinPipeline(unittest.TestCase):
    """Test various aspects of the built-in postings pipeline."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')

    def tearDown(self):
        reset_the_world()

    def test_rfc2369_headers(self):
        # Ensure that RFC 2369 List-* headers are added.
        msg = mfs("""\
From: Anne Person <anne@example.org>
To: test@example.com
Subject: a test

testing
""")
        msgdata = {}
        process(self._mlist, msg, msgdata,
                pipeline_name='default-posting-pipeline')
        self.assertEqual(msg['list-id'], '<test.example.com>')
        self.assertEqual(msg['list-post'], '<mailto:test@example.com>')
