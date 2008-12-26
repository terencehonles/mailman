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
import sys
import shutil
import logging
import tempfile

from pkg_resources import resource_string
from textwrap import dedent

from mailman.config import config
from mailman.core.initialize import initialize
from mailman.i18n import _
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
        # Read the testing config and push it.
        test_config += resource_string('mailman.testing', 'testing.cfg')
        config.push('test config', test_config)
        # Enable log message propagation.
        for logger_config in config.logger_configs:
            sub_name = logger_config.name.split('.')[-1]
            if sub_name == 'root':
                continue
            logger_name = 'mailman.' + sub_name
            log = logging.getLogger(logger_name)
            log.propagate = True
            log.setLevel(logging.DEBUG)
        # zope.testing sets up logging before we get to our own initialization
        # function.  This messes with the root logger, so explicitly set it to
        # go to stderr.
        if cls.stderr:
            console = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(config.logging.root.format,
                                          config.logging.root.datefmt)
            console.setFormatter(formatter)
            logging.getLogger().addHandler(console)

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

    # Flag to indicate that loggers should propagate to the console.
    stderr = False

    @classmethod
    def handle_stderr(cls, *ignore):
        cls.stderr = True

    @classmethod
    def hack_options_parser(cls):
        """Hack our way into the zc.testing framework.

        Add our custom command line option parsing into zc.testing's.  We do
        the imports here so that if zc.testing isn't invoked, this stuff never
        gets in the way.  This is pretty fragile, depend on changes in the
        zc.testing package.  There should be a better way!
        """
        from zope.testing.testrunner.options import parser
        parser.add_option('-e', '--stderr',
                          action='callback', callback=cls.handle_stderr,
                          help=_('Propagate log errors to stderr.'))



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
