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

"""Test some additional corner cases for starting/stopping."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'find_master',
    'make_config',
    ]


import os
import sys
import time
import errno
import signal
import shutil
import socket
import unittest

from datetime import timedelta, datetime

from mailman.commands.cli_control import Start, kill_watcher
from mailman.config import config
from mailman.testing.layers import ConfigLayer

SEP = '|'



def make_config():
    # All we care about is the master process; normally it starts a bunch of
    # runners, but we don't care about any of them, so write a test
    # configuration file for the master that disables all the runners.
    new_config = 'no-runners.cfg'
    config_file = os.path.join(os.path.dirname(config.filename), new_config)
    shutil.copyfile(config.filename, config_file)
    with open(config_file, 'a') as fp:
        for runner_config in config.runner_configs:
            print >> fp, '[{0}]\nstart:no\n'.format(runner_config.name)
    return config_file


def find_master():
    # See if the master process is still running.
    until = timedelta(seconds=10) + datetime.now()
    while datetime.now() < until:
        time.sleep(0.1)
        try:
            with open(config.PID_FILE) as fp:
                pid = int(fp.read().strip())
                os.kill(pid, 0)
        except IOError as error:
            if error.errno != errno.ENOENT:
                raise
        except ValueError:
            pass
        except OSError as error:
            if error.errno != errno.ESRCH:
                raise
        else:
            return pid
    else:
        return None



class FakeArgs:
    force = None
    run_as_user = None
    quiet = True
    config = None


class FakeParser:
    def __init__(self):
        self.message = None

    def error(self, message):
        self.message = message
        sys.exit(1)



class TestStart(unittest.TestCase):
    """Test various starting scenarios."""

    layer = ConfigLayer

    def setUp(self):
        self.command = Start()
        self.command.parser = FakeParser()
        self.args = FakeArgs()
        self.args.config = make_config()

    def tearDown(self):
        try:
            with open(config.PID_FILE) as fp:
                master_pid = int(fp.read())
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise
            # There is no master, so just ignore this.
            return
        kill_watcher(signal.SIGTERM)
        os.waitpid(master_pid, 0)

    def test_force_stale_lock(self):
        # Fake an acquisition of the master lock by another process, which
        # subsequently goes stale.  Start by finding a free process id.  Yes,
        # this could race, but given that we're starting with our own PID and
        # searching downward, it's less likely.
        fake_pid = os.getpid() - 1
        while fake_pid > 1:
            try:
                os.kill(fake_pid, 0)
            except OSError as error:
                if error.errno == errno.ESRCH:
                    break
            fake_pid -= 1
        else:
            raise RuntimeError('Cannot find free PID')
        # Lock acquisition logic taken from flufl.lock.
        claim_file = SEP.join((
            config.LOCK_FILE,
            socket.getfqdn(),
            str(fake_pid),
            '0'))
        with open(config.LOCK_FILE, 'w') as fp:
            fp.write(claim_file)
        os.link(config.LOCK_FILE, claim_file)
        expiration_date = datetime.now() - timedelta(minutes=2)
        t = time.mktime(expiration_date.timetuple())
        os.utime(claim_file, (t, t))
        # Start without --force; no master will be running.
        try:
            self.command.process(self.args)
        except SystemExit:
            pass
        self.assertEqual(find_master(), None)
        self.assertTrue('--force' in self.command.parser.message)
        # Start again, this time with --force.
        self.args.force = True
        self.command.process(self.args)
        pid = find_master()
        self.assertNotEqual(pid, None)
