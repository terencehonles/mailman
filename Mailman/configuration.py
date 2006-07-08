# Copyright (C) 2006 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Configuration file loading and management."""

import os
import errno

from Mailman import Defaults

_missing = object()



class Configuration(object):
    def load(self, filename=None):
        # Load the configuration from the named file, or if not given, search
        # in VAR_PREFIX for an etc/mailman.cfg file.  If that file is missing,
        # use Mailman/mm_cfg.py for backward compatibility.
        #
        # Whatever you find, create a namespace and execfile that file in it.
        # The values in that namespace are exposed as attributes on this
        # Configuration instance.
        if filename is None:
            filename = os.path.join(Defaults.VAR_PREFIX, 'etc', 'mailman.cfg')
        # Set up the execfile namespace
        ns = Defaults.__dict__.copy()
        # Prune a few things
        del ns['__file__']
        del ns['__name__']
        del ns['__doc__']
        # Attempt our first choice
        path = os.path.abspath(os.path.expanduser(filename))
        try:
            execfile(path, ns, ns)
        except EnvironmentError, e:
            if e.errno <> errno.ENOENT:
                raise
            # The file didn't exist, so try mm_cfg.py
            from Mailman import mm_cfg
            ns = mm_cfg.__dict__.copy()
        # Pull out the defaults
        PREFIX          = ns['PREFIX']
        VAR_PREFIX      = ns['VAR_PREFIX']
        EXEC_PREFIX     = ns['EXEC_PREFIX']
        # Now that we've loaded all the configuration files we're going to
        # load, set up some useful directories.
        self.LIST_DATA_DIR      = os.path.join(VAR_PREFIX, 'lists')
        self.LOG_DIR            = os.path.join(VAR_PREFIX, 'logs')
        self.LOCK_DIR = lockdir = os.path.join(VAR_PREFIX, 'locks')
        self.DATA_DIR = datadir = os.path.join(VAR_PREFIX, 'data')
        self.ETC_DIR = etcdir   = os.path.join(VAR_PREFIX, 'etc')
        self.SPAM_DIR           = os.path.join(VAR_PREFIX, 'spam')
        self.WRAPPER_DIR        = os.path.join(EXEC_PREFIX, 'mail')
        self.BIN_DIR            = os.path.join(PREFIX, 'bin')
        self.SCRIPTS_DIR        = os.path.join(PREFIX, 'scripts')
        self.TEMPLATE_DIR       = os.path.join(PREFIX, 'templates')
        self.MESSAGES_DIR       = os.path.join(PREFIX, 'messages')
        self.PUBLIC_ARCHIVE_FILE_DIR  = os.path.join(VAR_PREFIX,
                                                     'archives', 'public')
        self.PRIVATE_ARCHIVE_FILE_DIR = os.path.join(VAR_PREFIX,
                                                     'archives', 'private')
        # Directories used by the qrunner subsystem
        self.QUEUE_DIR = qdir   = os.path.join(VAR_PREFIX, 'qfiles')
        self.INQUEUE_DIR        = os.path.join(qdir, 'in')
        self.OUTQUEUE_DIR       = os.path.join(qdir, 'out')
        self.CMDQUEUE_DIR       = os.path.join(qdir, 'commands')
        self.BOUNCEQUEUE_DIR    = os.path.join(qdir, 'bounces')
        self.NEWSQUEUE_DIR      = os.path.join(qdir, 'news')
        self.ARCHQUEUE_DIR      = os.path.join(qdir, 'archive')
        self.SHUNTQUEUE_DIR     = os.path.join(qdir, 'shunt')
        self.VIRGINQUEUE_DIR    = os.path.join(qdir, 'virgin')
        self.BADQUEUE_DIR       = os.path.join(qdir, 'bad')
        self.RETRYQUEUE_DIR     = os.path.join(qdir, 'retry')
        self.MAILDIR_DIR        = os.path.join(qdir, 'maildir')
        # Other useful files
        self.PIDFILE                = os.path.join(datadir,
                                                   'master-qrunner.pid')
        self.SITE_PW_FILE           = os.path.join(datadir, 'adm.pw')
        self.LISTCREATOR_PW_FILE    = os.path.join(datadir, 'creator.pw')
        self.CONFIG_FILE            = os.path.join(etcdir, 'mailman.cfg')
        self.LOCK_FILE              = os.path.join(lockdir, 'master-qrunner')
        # Now update our dict so attribute syntax just works
        self.__dict__.update(ns)



config = Configuration()

