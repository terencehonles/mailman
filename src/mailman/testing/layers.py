# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

# XXX 2012-03-23 BAW: Layers really really suck.  For example, the
# test_owners_get_email() test requires that both the SMTPLayer and LMTPLayer
# be set up, but there's apparently no way to do that and make zope.testing
# happy.  This causes no tests failures, but it does cause errors at the end
# of the full test run.  For now, I'll ignore that, but I do want to
# eventually get rid of the zope.test* dependencies and use something like
# testresources or some such.

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ConfigLayer',
    'LMTPLayer',
    'MockAndMonkeyLayer',
    'RESTLayer',
    'SMTPLayer',
    'is_testing',
    ]


import os
import sys
import shutil
import logging
import datetime
import tempfile

from base64 import b64encode
from lazr.config import as_boolean, as_timedelta
from pkg_resources import resource_string
from textwrap import dedent
from urllib2 import Request, URLError, urlopen
from zope.component import getUtility

from mailman.config import config
from mailman.core import initialize
from mailman.core.initialize import INHIBIT_CONFIG_FILE
from mailman.core.logging import get_handler
from mailman.interfaces.domain import IDomainManager
from mailman.testing.helpers import (
    TestableMaster, get_lmtp_client, reset_the_world)
from mailman.testing.mta import ConnectionCountingController
from mailman.utilities.string import expand


TEST_TIMEOUT = datetime.timedelta(seconds=5)
NL = '\n'



class MockAndMonkeyLayer:
    """Layer for mocking and monkey patching for testing."""

    # Set this to True to enable predictable datetimes, uids, etc.
    testing_mode = False

    # A registration of all testing factories, for resetting between tests.
    _resets = []

    @classmethod
    def testTearDown(cls):
        for reset in cls._resets:
            reset()

    @classmethod
    def register_reset(cls, reset):
        cls._resets.append(reset)



class ConfigLayer(MockAndMonkeyLayer):
    """Layer for pushing and popping test configurations."""

    var_dir = None
    styles = None

    @classmethod
    def setUp(cls):
        # Set up the basic configuration stuff.  Turn off path creation until
        # we've pushed the testing config.
        config.create_paths = False
        initialize.initialize_1(INHIBIT_CONFIG_FILE)
        assert cls.var_dir is None, 'Layer already set up'
        # Calculate a temporary VAR_DIR directory so that run-time artifacts
        # of the tests won't tread on the installation's data.  This also
        # makes it easier to clean up after the tests are done, and insures
        # isolation of test suite runs.
        cls.var_dir = tempfile.mkdtemp()
        # We need a test configuration both for the foreground process and any
        # child processes that get spawned.  lazr.config would allow us to do
        # it all in a string that gets pushed, and we'll do that for the
        # foreground, but because we may be spawning processes (such as
        # runners) we'll need a file that we can specify to the with the -C
        # option.  Craft the full test configuration string here, push it, and
        # also write it out to a temp file for -C.
        test_config = dedent("""
        [mailman]
        layout: testing
        [passwords]
        password_scheme: cleartext
        [paths.testing]
        var_dir: %s
        [devmode]
        testing: yes
        """ % cls.var_dir)
        # Read the testing config and push it.
        test_config += resource_string('mailman.testing', 'testing.cfg')
        config.create_paths = True
        config.push('test config', test_config)
        # Initialize everything else.
        initialize.initialize_2()
        initialize.initialize_3()
        # When stderr debugging is enabled, subprocess root loggers should
        # also be more verbose.
        if cls.stderr:
            test_config += dedent("""
            [logging.root]
            propagate: yes
            level: debug
            """)
        # Enable log message propagation and reset the log paths so that the
        # doctests can check the output.
        for logger_config in config.logger_configs:
            sub_name = logger_config.name.split('.')[-1]
            if sub_name == 'root':
                continue
            logger_name = 'mailman.' + sub_name
            log = logging.getLogger(logger_name)
            log.propagate = True
            # Reopen the file to a new path that tests can get at.  Instead of
            # using the configuration file path though, use a path that's
            # specific to the logger so that tests can find expected output
            # more easily.
            path = os.path.join(config.LOG_DIR, sub_name)
            get_handler(sub_name).reopen(path)
            log.setLevel(logging.DEBUG)
            # If stderr debugging is enabled, make sure subprocesses are also
            # more verbose.
            if cls.stderr:
                test_config += expand(dedent("""
                [logging.$name]
                propagate: yes
                level: debug
                """), dict(name=sub_name, path=path))
        # zope.testing sets up logging before we get to our own initialization
        # function.  This messes with the root logger, so explicitly set it to
        # go to stderr.
        if cls.stderr:
            console = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(config.logging.root.format,
                                          config.logging.root.datefmt)
            console.setFormatter(formatter)
            logging.getLogger().addHandler(console)
        # Write the configuration file for subprocesses and set up the config
        # object to pass that properly on the -C option.
        config_file = os.path.join(cls.var_dir, 'test.cfg')
        with open(config_file, 'w') as fp:
            fp.write(test_config)
            print >> fp
        config.filename = config_file

    @classmethod
    def tearDown(cls):
        assert cls.var_dir is not None, 'Layer not set up'
        config.pop('test config')
        shutil.rmtree(cls.var_dir)
        cls.var_dir = None

    @classmethod
    def testSetUp(cls):
        # Add an example domain.
        getUtility(IDomainManager).add(
            'example.com', 'An example domain.',
            'http://lists.example.com', 'postmaster@example.com')
        config.db.commit()

    @classmethod
    def testTearDown(cls):
        reset_the_world()

    # Flag to indicate that loggers should propagate to the console.
    stderr = False

    @classmethod
    def enable_stderr(cls):
        """Enable stderr logging if -e/--stderr is given.

        We used to hack our way into the zc.testing framework, but that was
        undocumented and way too fragile.  Well, this probably is too, but now
        we just scan sys.argv for -e/--stderr and enable logging if found.
        Then we remove the option from sys.argv.  This works because this
        method is called before zope.testrunner sees the options.

        As a bonus, we'll check an environment variable too.
        """
        if '-e' in sys.argv:
            cls.stderr = True
            sys.argv.remove('-e')
        if '--stderr' in sys.argv:
            cls.stderr = True
            sys.argv.remove('--stderr')
        if len(os.environ.get('MM_VERBOSE_TESTLOG', '').strip()) > 0:
            cls.stderr = True

    # The top of our source tree, for tests that care (e.g. hooks.txt).
    root_directory = None

    @classmethod
    def set_root_directory(cls, directory):
        """Set the directory at the root of our source tree.

        zc.recipe.testrunner runs from parts/test/working-directory, but
        that's actually changed over the life of the package.  Some tests
        care, e.g. because they need to find our built-out bin directory.
        Fortunately, buildout can give us this information.  See the
        `buildout.cfg` file for where this method is called.
        """
        cls.root_directory = directory



class SMTPLayer(ConfigLayer):
    """Layer for starting, stopping, and accessing a test SMTP server."""

    smtpd = None

    @classmethod
    def setUp(cls):
        assert cls.smtpd is None, 'Layer already set up'
        host = config.mta.smtp_host
        port = int(config.mta.smtp_port)
        cls.smtpd = ConnectionCountingController(host, port)
        cls.smtpd.start()

    @classmethod
    def tearDown(cls):
        assert cls.smtpd is not None, 'Layer not set up'
        cls.smtpd.clear()
        cls.smtpd.stop()

    @classmethod
    def testSetUp(cls):
        # Make sure we don't call our superclass's testSetUp(), otherwise the
        # example.com domain will get added twice.
        pass

    @classmethod
    def testTearDown(cls):
        cls.smtpd.reset()
        cls.smtpd.clear()



class LMTPLayer(ConfigLayer):
    """Layer for starting, stopping, and accessing a test LMTP server."""

    lmtpd = None

    @staticmethod
    def _wait_for_lmtp_server():
        get_lmtp_client(quiet=True)

    @classmethod
    def setUp(cls):
        assert cls.lmtpd is None, 'Layer already set up'
        cls.lmtpd = TestableMaster(cls._wait_for_lmtp_server)
        cls.lmtpd.start('lmtp')

    @classmethod
    def tearDown(cls):
        assert cls.lmtpd is not None, 'Layer not set up'
        cls.lmtpd.stop()
        cls.lmtpd = None

    @classmethod
    def testSetUp(cls):
        # Make sure we don't call our superclass's testSetUp(), otherwise the
        # example.com domain will get added twice.
        pass



class RESTLayer(SMTPLayer):
    """Layer for starting, stopping, and accessing the test REST layer."""

    server = None

    @staticmethod
    def _wait_for_rest_server():
        until = datetime.datetime.now() + as_timedelta(config.devmode.wait)
        while datetime.datetime.now() < until:
            try:
                request = Request('http://localhost:9001/3.0/system')
                basic_auth = '{0}:{1}'.format(config.webservice.admin_user,
                                              config.webservice.admin_pass)
                request.add_header('Authorization',
                                   'Basic ' + b64encode(basic_auth))
                fp = urlopen(request)
            except URLError:
                pass
            else:
                fp.close()
                break
        else:
            raise RuntimeError('REST server did not start up')

    @classmethod
    def setUp(cls):
        assert cls.server is None, 'Layer already set up'
        cls.server = TestableMaster(cls._wait_for_rest_server)
        cls.server.start('rest')

    @classmethod
    def tearDown(cls):
        assert cls.server is not None, 'Layer not set up'
        cls.server.stop()
        cls.server = None



def is_testing():
    """Return a 'testing' flag for use with the predictable factories.

    :return: True when in testing mode.
    :rtype: bool
    """
    return (MockAndMonkeyLayer.testing_mode or
            as_boolean(config.devmode.testing))
