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

__metaclass__ = type
__all__ = [
    'Configuration',
    ]


import os
import sys
import errno
import logging

from StringIO import StringIO
from lazr.config import ConfigSchema
from lazr.config.interfaces import NoCategoryError
from pkg_resources import resource_filename

from mailman import Defaults
from mailman import version
from mailman.config.helpers import as_boolean
from mailman.core import errors
from mailman.domain import Domain
from mailman.languages import LanguageManager


SPACE = ' '



class Configuration(object):
    """The core global configuration object."""

    def __init__(self):
        self.domains = {}       # email host -> IDomain
        self.qrunners = {}
        self.qrunner_shortcuts = {}
        self.languages = LanguageManager()
        self.QFILE_SCHEMA_VERSION = version.QFILE_SCHEMA_VERSION
        self._config = None
        # Create various registries.
        self.archivers = {}
        self.chains = {}
        self.rules = {}
        self.handlers = {}
        self.pipelines = {}
        self.commands = {}

    def _clear(self):
        """Clear the cached configuration variables."""
        self.domains.clear()
        self.qrunners.clear()
        self.qrunner_shortcuts.clear()
        self.languages = LanguageManager()

    def __getattr__(self, name):
        """Delegate to the configuration object."""
        return getattr(self._config, name)

    def load(self, filename=None):
        """Load the configuration from the schema and config files."""
        schema_file = resource_filename('mailman.config', 'schema.cfg')
        schema = ConfigSchema(schema_file)
        # If a configuration file was given, load it now too.
        if filename is None:
            self._config = schema.loadFile(StringIO(''), '<default>')
        else:
            self._config = schema.load(filename)
        self._post_process()

    def push(self, config_name, config_string):
        """Push a new configuration onto the stack."""
        self._clear()
        self._config.push(config_name, config_string)
        self._post_process()

    def pop(self, config_name):
        """Pop a configuration from the stack."""
        self._clear()
        self._config.pop(config_name)
        self._post_process()

    def _post_process(self):
        """Perform post-processing after loading the configuration files."""
        # Set up the domains.
        try:
            domains = self._config.getByCategory('domain')
        except NoCategoryError:
            domains = []
        for section in domains:
            domain = Domain(section.email_host, section.base_url,
                            section.description, section.contact_address)
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
        # Set up the queue runners.
        try:
            qrunners = self._config.getByCategory('qrunner')
        except NoCategoryError:
            qrunners = []
        for section in qrunners:
            if not as_boolean(section.start):
                continue
            name = section['class']
            self.qrunners[name] = section.count
            # Calculate the queue runner shortcut name.
            classname = name.rsplit('.', 1)[1]
            if classname.endswith('Runner'):
                shortname = classname[:-6].lower()
            else:
                shortname = classname
            self.qrunner_shortcuts[shortname] = section['class']
        # Set up directories.
        self.BIN_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
        VAR_DIR = self._config.mailman.var_dir
        # Now that we've loaded all the configuration files we're going to
        # load, set up some useful directories.
        join = os.path.join
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
        # Set up all the languages.
        try:
            languages = self._config.getByCategory('language')
        except NoCategoryError:
            languages = []
        for section in languages:
            code = section.name.split('.')[1]
            self.languages.add_language(code, section.description,
                                        section.charset, section.enable)
        # Always enable the server default language, which must be defined.
        self.languages.enable_language(self._config.mailman.default_language)

    @property
    def logger_configs(self):
        """Return all log config sections."""
        try:
            loggers = self._config.getByCategory('logging')
        except NoCategoryError:
            loggers = []
        return loggers

    @property
    def paths(self):
        """Return a substitution dictionary of all path variables."""
        return dict((k, self.__dict__[k])
                    for k in self.__dict__
                    if k.endswith('_DIR'))

    def ensure_directories_exist(self):
        """Create all path directories if they do not exist."""
        for variable, directory in self.paths.items():
            try:
                os.makedirs(directory, 02775)
            except OSError, e:
                if e.errno <> errno.EEXIST:
                    raise

    @property
    def header_matches(self):
        """Iterate over all spam matching headers.

        Values are 3-tuples of (header, pattern, chain)
        """
        try:
            matches = self._config.getByCategory('spam.headers')
        except NoCategoryError:
            matches = []
        for match in matches:
            yield (matches.header, matches.pattern, matches.chain)
