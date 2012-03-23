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

"""Test the pipeline runner."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestPipelineRunner',
    ]


import unittest

from zope.interface import implements

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.handler import IHandler
from mailman.interfaces.pipeline import IPipeline
from mailman.runners.pipeline import PipelineRunner
from mailman.testing.helpers import (
    make_testable_runner,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class MyTestHandler:
    implements(IHandler)
    name = 'test handler'
    description = 'A test handler'

    def __init__(self, marker, test):
        self._marker = marker
        self._test = test

    def process(self, mlist, msg, msgdata):
        self._test.mark(self._marker)


class MyTestPipeline:
    implements(IPipeline)
    name = 'test'
    description = 'a test pipeline'

    def __init__(self, marker, test):
        self._marker = marker
        self._test = test

    def __iter__(self):
        yield MyTestHandler(self._marker, self._test)



class TestPipelineRunner(unittest.TestCase):
    """Test the pipeline runner."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.posting_pipeline = 'test posting'
        self._mlist.owner_pipeline = 'test owner'
        config.pipelines['test posting'] = MyTestPipeline('posting', self)
        config.pipelines['test owner'] = MyTestPipeline('owner', self)
        self._pipeline = make_testable_runner(PipelineRunner, 'pipeline')
        self._markers = []
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com

""")

    def tearDown(self):
        del config.pipelines['test posting']
        del config.pipelines['test owner']

    def mark(self, marker):
        # Record a marker seen by a handler.
        self._markers.append(marker)

    def test_posting(self):
        # A message accepted for posting gets processed through the posting
        # pipeline.
        msgdata = dict(listname='test@example.com')
        config.switchboards['pipeline'].enqueue(self._msg, msgdata)
        self._pipeline.run()
        self.assertEqual(len(self._markers), 1)
        self.assertEqual(self._markers[0], 'posting')

    def test_owner(self):
        # A message accepted for posting to a list's owners gets processed
        # through the owner pipeline.
        msgdata = dict(listname='test@example.com',
                       to_owner=True)
        config.switchboards['pipeline'].enqueue(self._msg, msgdata)
        self._pipeline.run()
        self.assertEqual(len(self._markers), 1)
        self.assertEqual(self._markers[0], 'owner')
