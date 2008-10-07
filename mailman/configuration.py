# Copyright (C) 2006-2008 by the Free Software Foundation, Inc.
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

"""Configuration file loading and management."""

import os
import sys
import errno

from mailman import Defaults
from mailman import version
from mailman.core import errors
from mailman.domain import Domain
from mailman.languages import LanguageManager

SPACE = ' '
_missing = object()

DEFAULT_QRUNNERS = (
    '.archive.ArchiveRunner',
    '.bounce.BounceRunner',
    '.command.CommandRunner',
    '.incoming.IncomingRunner',
    '.news.NewsRunner',
    '.outgoing.OutgoingRunner',
    '.pipeline.PipelineRunner',
    '.retry.RetryRunner',
    '.virgin.VirginRunner',
    )



class Configuration(object):
    def __init__(self):
        self.domains = {}       # email host -> IDomain
        self.qrunners = {}
        self.qrunner_shortcuts = {}
        self.QFILE_SCHEMA_VERSION = version.QFILE_SCHEMA_VERSION

    def load(self, filename=None):
        join = os.path.join
        # Set up the execfile namespace
        ns = Defaults.__dict__.copy()
        # Prune a few things, add a few things
        del ns['__file__']
        del ns['__name__']
        del ns['__doc__']
        ns['add_domain'] = self.add_domain
        ns['add_qrunner'] = self.add_qrunner
        ns['del_qrunner'] = self.del_qrunner
        self._languages = LanguageManager()
        ns['add_language'] = self._languages.add_language
        ns['enable_language'] = self._languages.enable_language
        # Add all known languages, but don't enable them.
        for code, (desc, charset) in Defaults._DEFAULT_LANGUAGE_DATA.items():
            self._languages.add_language(code, desc, charset, False)
        # Set up the default list of qrunners so that the mailman.cfg file may
        # add or delete them.
        for name in DEFAULT_QRUNNERS:
            self.add_qrunner(name)
        # Load the configuration from the named file, or if not given, search
        # around for a mailman.cfg file.  Whatever you find, create a
        # namespace and execfile that file in it.  The values in that
        # namespace are exposed as attributes on this Configuration instance.
        self.filename = None
        self.BIN_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
        dev_dir = os.path.dirname(self.BIN_DIR)
        paths = [
            # Development directories.
            join(dev_dir, 'var', 'etc', 'mailman.cfg'),
            join(os.getcwd(), 'var', 'etc', 'mailman.cfg'),
            join(os.getcwd(), 'etc', 'mailman.cfg'),
            # Standard installation directories.
            join('/etc', 'mailman.cfg'),
            join(Defaults.DEFAULT_VAR_DIRECTORY, 'etc', 'mailman.cfg'),
            ]
        if filename is not None:
            paths.insert(0, filename)
        for cfg_path in paths:
            path = os.path.abspath(os.path.expanduser(cfg_path))
            try:
                execfile(path, ns, ns)
            except EnvironmentError, e:
                if e.errno <> errno.ENOENT:
                    # It's okay if the mailman.cfg file does not exist.  This
                    # can happen for example in the test suite.
                    raise
            else:
                self.filename = cfg_path
                break
        if self.filename is None:
            # The logging subsystem isn't running yet, so use stderr.
            print >> sys.stderr, 'No runtime configuration file file.  Use -C'
            sys.exit(-1)
        # Based on values possibly set in mailman.cfg, add additional qrunners.
        if ns['USE_MAILDIR']:
            self.add_qrunner('.maildir.MaildirRunner')
        if ns['USE_LMTP']:
            self.add_qrunner('.lmtp.LMTPRunner')
        # Pull out the defaults.
        VAR_DIR = os.path.abspath(ns['VAR_DIR'])
        # Now that we've loaded all the configuration files we're going to
        # load, set up some useful directories.
        self.LIST_DATA_DIR      = join(VAR_DIR, 'lists')
        self.LOG_DIR            = join(VAR_DIR, 'logs')
        self.LOCK_DIR = lockdir = join(VAR_DIR, 'locks')
        self.DATA_DIR = datadir = join(VAR_DIR, 'data')
        self.ETC_DIR = etcdir   = join(VAR_DIR, 'etc')
        self.SPAM_DIR           = join(VAR_DIR, 'spam')
        self.EXT_DIR            = join(VAR_DIR, 'ext')
        self.PUBLIC_ARCHIVE_FILE_DIR  = join(VAR_DIR, 'archives', 'public')
        self.PRIVATE_ARCHIVE_FILE_DIR = join(VAR_DIR, 'archives', 'private')
        # Directories used by the qrunner subsystem
        self.QUEUE_DIR = qdir   = join(VAR_DIR, 'qfiles')
        self.ARCHQUEUE_DIR      = join(qdir, 'archive')
        self.BADQUEUE_DIR       = join(qdir, 'bad')
        self.BOUNCEQUEUE_DIR    = join(qdir, 'bounces')
        self.CMDQUEUE_DIR       = join(qdir, 'commands')
        self.INQUEUE_DIR        = join(qdir, 'in')
        self.MAILDIR_DIR        = join(qdir, 'maildir')
        self.NEWSQUEUE_DIR      = join(qdir, 'news')
        self.OUTQUEUE_DIR       = join(qdir, 'out')
        self.PIPELINEQUEUE_DIR  = join(qdir, 'pipeline')
        self.RETRYQUEUE_DIR     = join(qdir, 'retry')
        self.SHUNTQUEUE_DIR     = join(qdir, 'shunt')
        self.VIRGINQUEUE_DIR    = join(qdir, 'virgin')
        self.MESSAGES_DIR       = join(VAR_DIR, 'messages')
        # Other useful files
        self.PIDFILE                = join(datadir, 'master-qrunner.pid')
        self.SITE_PW_FILE           = join(datadir, 'adm.pw')
        self.LISTCREATOR_PW_FILE    = join(datadir, 'creator.pw')
        self.CONFIG_FILE            = join(etcdir, 'mailman.cfg')
        self.LOCK_FILE              = join(lockdir, 'master-qrunner')
        # Now update our dict so attribute syntax just works
        del ns['add_domain']
        del ns['add_qrunner']
        del ns['del_qrunner']
        self.__dict__.update(ns)
        # Enable all specified languages, and promote the language manager to
        # a public attribute.
        self.languages = self._languages
        del self._languages
        available_languages = set(self._DEFAULT_LANGUAGE_DATA)
        enabled_languages = set(self.LANGUAGES.split())
        if 'all' in enabled_languages:
            languages = available_languages
        else:
            unknown_language = enabled_languages - available_languages
            if unknown_language:
                print >> sys.stderr, 'Ignoring unknown language codes:', \
                      SPACE.join(unknown_language)
            languages = available_languages & enabled_languages
        for code in languages:
            self.languages.enable_language(code)
        # Always add and enable the default server language.
        code = self.DEFAULT_SERVER_LANGUAGE
        self.languages.enable_language(code)
        # Create various registries.
        self.archivers = {}
        self.chains = {}
        self.rules = {}
        self.handlers = {}
        self.pipelines = {}
        self.commands = {}

    def add_domain(self, *args, **kws):
        """Add a virtual domain.

        See `Domain`.
        """
        domain = Domain(*args, **kws)
        if domain.email_host in self.domains:
            raise errors.BadDomainSpecificationError(
                'Duplicate email host: %s' % domain.email_host)
        # Make sure there's only one mapping for the url_host
        if domain.url_host in self.domains.values():
            raise errors.BadDomainSpecificationError(
                'Duplicate url host: %s' % domain.url_host)
        # We'll do the reverse mappings on-demand.  There shouldn't be too
        # many virtual hosts that it will really matter that much.
        self.domains[domain.email_host] = domain

    # Proxy the docstring for the above method.
    add_domain.__doc__ = Domain.__init__.__doc__

    def add_qrunner(self, name, count=1):
        """Convenient interface for adding additional qrunners.

        :param name: the qrunner name, which must not include the 'Runner'
            suffix.  E.g. 'HTTP' or 'LMTP'.
        :param count: is the number of qrunner slices to create, default: 1.
        """
        if name.startswith('.'):
            name = 'mailman.queue' + name
        self.qrunners[name] = count
        # Calculate the queue runner shortcut name.
        classname = name.rsplit('.', 1)[1]
        if classname.endswith('Runner'):
            shortname = classname[:-6].lower()
        else:
            shortname = classname
        self.qrunner_shortcuts[shortname] = name

    def del_qrunner(self, name):
        """Remove the named qrunner so that it does not start.

        :param name: the qrunner name, which must not include the 'Runner'
            suffix.
        """
        if name.startswith('.'):
            name = 'mailman.queue' + name
        self.qrunners.pop(name)
        for shortname, classname in self.qrunner_shortcuts:
            if name == classname:
                del self.qrunner_shortcuts[shortname]
                break

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
