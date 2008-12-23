# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""Mailman test layers."""

__metaclass__ = type
__all__ = [
    'ConfigLayer',
    'SMTPLayer',
    ]


import os
import shutil
import tempfile

from pkg_resources import resource_string
from textwrap import dedent

from mailman.config import config
from mailman.core.initialize import initialize
from mailman.testing.helpers import SMTPServer


NL = '\n'



class ConfigLayer:
    """Layer for pushing and popping test configurations."""

    var_dir = None

    @classmethod
    def setUp(cls):
        initialize()
        assert cls.var_dir is None, 'Layer already set up'
        # Calculate a temporary VAR_DIR directory so that run-time artifacts
        # of the tests won't tread on the installation's data.  This also
        # makes it easier to clean up after the tests are done, and insures
        # isolation of test suite runs.
        cls.var_dir = tempfile.mkdtemp()
        # Create a section with the var directory.
        test_config = dedent("""
        [mailman]
        var_dir: %s
        """ % cls.var_dir)
        # Read the testing config, but don't push it yet.
        test_config += resource_string('mailman.testing', 'testing.cfg')
        config.push('test config', test_config)

    @classmethod
    def tearDown(cls):
        assert cls.var_dir is not None, 'Layer not set up'
        config.pop('test config')
        shutil.rmtree(cls.var_dir)
        cls.var_dir = None

    @classmethod
    def testSetUp(self):
        pass

    @classmethod
    def testTearDown(self):
        # Reset the database between tests.
        config.db._reset()
        # Remove all residual queue files.
        for dirpath, dirnames, filenames in os.walk(config.QUEUE_DIR):
            for filename in filenames:
                os.remove(os.path.join(dirpath, filename))
        # Clear out messages in the message store.
        for message in config.db.message_store.messages:
            config.db.message_store.delete_message(message['message-id'])
        config.db.commit()



class SMTPLayer(ConfigLayer):
    """Layer for starting, stopping, and accessing a test SMTP server."""

    smtpd = None

    @classmethod
    def setUp(cls):
        assert cls.smtpd is None, 'Layer already set up'
        cls.smtpd = SMTPServer()
        cls.smtpd.start()

    @classmethod
    def tearDown(cls):
        assert cls.smtpd is not None, 'Layer not set up'
        cls.smtpd.clear()
        cls.smtpd.stop()

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass
