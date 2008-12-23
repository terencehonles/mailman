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
import textwrap

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
        test_config = []
        # Calculate a temporary VAR_DIR directory so that run-time artifacts
        # of the tests won't tread on the installation's data.  This also
        # makes it easier to clean up after the tests are done, and insures
        # isolation of test suite runs.
        cls.var_dir = tempfile.mkdtemp()
        # lazr.config says it doesn't care about indentation, but we've
        # actually got mixed indentation above because of the for-loop.  It's
        # just safer to dedent the whole string now.
        test_config.append(textwrap.dedent("""
        [mailman]
        var_dir: %s
        """ % cls.var_dir))
        # Push a high port for our test SMTP server.
        test_config.append(textwrap.dedent("""
        [mta]
        smtp_port: 9025
        """))
        # Set the qrunners to exit after one error.
        for qrunner in config.qrunner_shortcuts:
            test_config.append(textwrap.dedent("""
            [qrunner.%s]
            max_restarts: 1
            """ % qrunner))
        # Add stuff for the archiver and a sample domain.
        test_config.append(textwrap.dedent("""
        [archiver.mail_archive]
        base_url: http://go.mail-archive.dev/
        recipient: archive@mail-archive.dev

        [domain.example_dot_com]
        email_host: example.com
        base_url: http://www.example.com
        contact_address: postmaster@example.com
        """))
        config_string = NL.join(test_config)
        import pdb; pdb.set_trace()
        config.push('test config', config_string)
        config._config.getByCategory('domain')

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
