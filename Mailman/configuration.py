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
from Mailman import Errors

_missing = object()



class Configuration(object):
    def __init__(self):
        self.domains = {}       # email host -> web host
        self._reverse = None

    def load(self, filename=None):
        # Load the configuration from the named file, or if not given, search
        # in VAR_PREFIX for an etc/mailman.cfg file.  If that file is missing,
        # use Mailman/mm_cfg.py for backward compatibility.
        #
        # Whatever you find, create a namespace and execfile that file in it.
        # The values in that namespace are exposed as attributes on this
        # Configuration instance.
        original_filename = filename
        if filename is None:
            filename = os.path.join(Defaults.VAR_PREFIX, 'etc', 'mailman.cfg')
        # Set up the execfile namespace
        ns = Defaults.__dict__.copy()
        # Prune a few things, add a few things
        del ns['__file__']
        del ns['__name__']
        del ns['__doc__']
        ns['add_domain'] = self.add_domain
        ns['add_runner'] = self.add_runner
        # Attempt our first choice
        path = os.path.abspath(os.path.expanduser(filename))
        try:
            execfile(path, ns, ns)
        except EnvironmentError, e:
            if e.errno <> errno.ENOENT or original_filename:
                raise
            # The file didn't exist, so try mm_cfg.py
            from Mailman import mm_cfg
            ns.update(mm_cfg.__dict__)
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
        if 'add_domain' in ns:
            del ns['add_domain']
        if 'add_runner' in ns:
            del ns['add_runner']
        self.__dict__.update(ns)
        # Add the default domain if there are no virtual domains currently
        # defined.
        if not self.domains:
            self.add_domain(self.DEFAULT_EMAIL_HOST, self.DEFAULT_URL_HOST)

    def add_domain(self, email_host, url_host):
        """Add the definition of a virtual domain.

        email_host is the right-hand side of the posting email address,
        e.g. 'example.com' in 'mylist@example.com'.  url_host is the host name
        part of the exposed web pages, e.g. 'www.example.com'."""
        if email_host in self.domains:
            raise Errors.BadDomainSpecificationError(
                'Duplicate email host: %s' % email_host)
        # Make sure there's only one mapping for the url_host
        if url_host in self.domains.values():
            raise Errors.BadDomainSpecificationError(
                'Duplicate url host: %s' % url_host)
        # We'll do the reverse mappings on-demand.  There shouldn't be too
        # many virtual hosts that it will really matter that much.
        self.domains[email_host] = url_host
        # Invalidate the reverse mapping cache
        self._reverse = None

    # Given an email host name, the url host name can be looked up directly.
    # This does the reverse mapping.
    def get_email_host(self, url_host, default=None):
        if self._reverse is None:
            # XXX Can't use a generator comprehension until Python 2.4 is
            # minimum requirement.
            self._reverse = dict([(v, k) for k, v in self.domains.items()])
        return self._reverse.get(url_host, default)

    def add_runner(self, name, count=1):
        """Convenient interface for adding additional qrunners.

        name is the qrunner name, and must include the 'Runner' suffix.
        E.g. 'HTTPRunner' or 'LMTPRunner'.  count is the number of qrunner
        slices to create, by default, 1.
        """
        self.QRUNNERS.append((name, count))

    @property
    def paths(self):
        return dict([(k, self.__dict__[k])
                     for k in self.__dict__
                     if k.endswith('_DIR')])



config = Configuration()
