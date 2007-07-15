# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

DEFAULT_QRUNNERS = (
    'Arch',
    'Bounce',
    'Command',
    'Incoming',
    'News',
    'Outgoing',
    'Retry',
    'Virgin',
    )



class Configuration(object):
    def __init__(self):
        self.domains = {}       # email host -> web host
        self._reverse = None
        self.qrunners = {}

    def load(self, filename=None):
        join = os.path.join
        # Load the configuration from the named file, or if not given, search
        # in the runtime data directory for an etc/mailman.cfg file.  If that
        # file is missing, use Mailman/mm_cfg.py for backward compatibility.
        #
        # Whatever you find, create a namespace and execfile that file in it.
        # The values in that namespace are exposed as attributes on this
        # Configuration instance.
        original_filename = filename
        if filename is None:
            filename = join(Defaults.RUNTIME_DIR, 'etc', 'mailman.cfg')
        # Set up the execfile namespace
        ns = Defaults.__dict__.copy()
        # Prune a few things, add a few things
        del ns['__file__']
        del ns['__name__']
        del ns['__doc__']
        ns['add_domain']  = self.add_domain
        ns['add_qrunner'] = self.add_qrunner
        ns['del_qrunner'] = self.del_qrunner
        # Set up the default list of qrunners so that the mailman.cfg file may
        # add or delete them.
        for name in DEFAULT_QRUNNERS:
            self.add_qrunner(name)
        # Attempt our first choice
        path = os.path.abspath(os.path.expanduser(filename))
        print 'path:', path
        try:
            execfile(path, ns, ns)
            self.filename = path
        except EnvironmentError, e:
            if e.errno <> errno.ENOENT or original_filename:
                raise
            # The file didn't exist, so try mm_cfg.py
            from Mailman import mm_cfg
            ns.update(mm_cfg.__dict__)
            self.filename = None
        # Based on values possibly set in mailman.cfg, add additional qrunners
        if ns['USE_MAILDIR']:
            self.add_qrunner('Maildir')
        if ns['USE_LMTP']:
            self.add_qrunner('LMTP')
        # Pull out the defaults
        RUNTIME_DIR     = ns['RUNTIME_DIR']
        # Now that we've loaded all the configuration files we're going to
        # load, set up some useful directories.
        self.LIST_DATA_DIR      = join(RUNTIME_DIR, 'lists')
        self.LOG_DIR            = join(RUNTIME_DIR, 'logs')
        self.LOCK_DIR = lockdir = join(RUNTIME_DIR, 'locks')
        self.DATA_DIR = datadir = join(RUNTIME_DIR, 'data')
        self.ETC_DIR = etcdir   = join(RUNTIME_DIR, 'etc')
        self.SPAM_DIR           = join(RUNTIME_DIR, 'spam')
        self.EXT_DIR            = join(RUNTIME_DIR, 'ext')
        self.PUBLIC_ARCHIVE_FILE_DIR  = join(RUNTIME_DIR, 'archives', 'public')
        self.PRIVATE_ARCHIVE_FILE_DIR = join(
            RUNTIME_DIR, 'archives', 'private')
        # Directories used by the qrunner subsystem
        self.QUEUE_DIR = qdir   = join(RUNTIME_DIR, 'qfiles')
        self.INQUEUE_DIR        = join(qdir, 'in')
        self.OUTQUEUE_DIR       = join(qdir, 'out')
        self.CMDQUEUE_DIR       = join(qdir, 'commands')
        self.BOUNCEQUEUE_DIR    = join(qdir, 'bounces')
        self.NEWSQUEUE_DIR      = join(qdir, 'news')
        self.ARCHQUEUE_DIR      = join(qdir, 'archive')
        self.SHUNTQUEUE_DIR     = join(qdir, 'shunt')
        self.VIRGINQUEUE_DIR    = join(qdir, 'virgin')
        self.BADQUEUE_DIR       = join(qdir, 'bad')
        self.RETRYQUEUE_DIR     = join(qdir, 'retry')
        self.MAILDIR_DIR        = join(qdir, 'maildir')
        # Other useful files
        self.PIDFILE                = join(datadir, 'master-qrunner.pid')
        self.SITE_PW_FILE           = join(datadir, 'adm.pw')
        self.LISTCREATOR_PW_FILE    = join(datadir, 'creator.pw')
        self.CONFIG_FILE            = join(etcdir, 'mailman.cfg')
        self.LOCK_FILE              = join(lockdir, 'master-qrunner')
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

    def add_qrunner(self, name, count=1):
        """Convenient interface for adding additional qrunners.

        name is the qrunner name and it must not include the 'Runner' suffix.
        E.g. 'HTTP' or 'LMTP'.  count is the number of qrunner slices to
        create, by default, 1.
        """
        name += 'Runner'
        self.qrunners[name] = count

    def del_qrunner(self, name):
        """Remove the named qrunner so that it does not start.

        name is the qrunner name and it must not include the 'Runner' suffix.
        """
        name += 'Runner'
        self.qrunners.pop(name)

    @property
    def paths(self):
        return dict([(k, self.__dict__[k])
                     for k in self.__dict__
                     if k.endswith('_DIR')])

    def ensure_directories_exist(self):
        for variable, directory in self.paths.items():
            try:
                os.makedirs(directory, 02775)
            except OSError, e:
                if e.errno <> errno.EEXIST:
                    raise



config = Configuration()
