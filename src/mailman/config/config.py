# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Configuration',
    ]


import os
import sys
import errno
import logging

from lazr.config import ConfigSchema, as_boolean
from pkg_resources import resource_stream
from zope.interface import Interface, implements

from mailman import version
from mailman.core import errors
from mailman.languages.manager import LanguageManager
from mailman.styles.manager import StyleManager
from mailman.utilities.filesystem import makedirs
from mailman.utilities.modules import call_name


SPACE = ' '



class IConfiguration(Interface):
    """Marker interface; used for adaptation in the REST API."""



class Configuration:
    """The core global configuration object."""

    implements(IConfiguration)

    def __init__(self):
        self.switchboards = {}
        self.languages = LanguageManager()
        self.style_manager = StyleManager()
        self.QFILE_SCHEMA_VERSION = version.QFILE_SCHEMA_VERSION
        self._config = None
        self.filename = None
        # Create various registries.
        self.chains = {}
        self.rules = {}
        self.handlers = {}
        self.pipelines = {}
        self.commands = {}

    def _clear(self):
        """Clear the cached configuration variables."""
        self.switchboards.clear()
        self.languages = LanguageManager()

    def __getattr__(self, name):
        """Delegate to the configuration object."""
        return getattr(self._config, name)

    def load(self, filename=None):
        """Load the configuration from the schema and config files."""
        schema_file = config_file = None
        try:
            schema_file = resource_stream('mailman.config', 'schema.cfg')
            schema = ConfigSchema('schema.cfg', schema_file)
            # If a configuration file was given, load it now too.  First, load
            # the absolute minimum default configuration, then if a
            # configuration filename was given by the user, push it.
            config_file = resource_stream('mailman.config', 'mailman.cfg')
            self._config = schema.loadFile(config_file, 'mailman.cfg')
            if filename is not None:
                self.filename = filename
                with open(filename) as user_config:
                    self._config.push(filename, user_config.read())
        finally:
            if schema_file:
                schema_file.close()
            if config_file:
                config_file.close()
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
        # Set up directories.
        self.BIN_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.VAR_DIR = var_dir = self._config.mailman.var_dir
        # Now that we've loaded all the configuration files we're going to
        # load, set up some useful directories.
        join = os.path.join
        self.LIST_DATA_DIR      = join(var_dir, 'lists')
        self.LOG_DIR            = join(var_dir, 'logs')
        self.LOCK_DIR = lockdir = join(var_dir, 'locks')
        self.DATA_DIR = datadir = join(var_dir, 'data')
        self.ETC_DIR = etcdir   = join(var_dir, 'etc')
        self.SPAM_DIR           = join(var_dir, 'spam')
        self.EXT_DIR            = join(var_dir, 'ext')
        self.QUEUE_DIR          = join(var_dir, 'qfiles')
        self.MESSAGES_DIR       = join(var_dir, 'messages')
        self.PUBLIC_ARCHIVE_FILE_DIR  = join(var_dir, 'archives', 'public')
        self.PRIVATE_ARCHIVE_FILE_DIR = join(var_dir, 'archives', 'private')
        # Other useful files
        self.PIDFILE                = join(datadir, 'master-qrunner.pid')
        self.SITE_PW_FILE           = join(datadir, 'adm.pw')
        self.LISTCREATOR_PW_FILE    = join(datadir, 'creator.pw')
        self.CONFIG_FILE            = join(etcdir, 'mailman.cfg')
        self.LOCK_FILE              = join(lockdir, 'master-qrunner')
        # Set up the switchboards.
        from mailman.queue import Switchboard
        Switchboard.initialize()
        # Set up all the languages.
        languages = self._config.getByCategory('language', [])
        for language in languages:
            if language.enabled:
                code = language.name.split('.')[1]
                self.languages.add(
                    code, language.charset, language.description)
        # The default language must always be available.
        assert self._config.mailman.default_language in self.languages
        self.ensure_directories_exist()
        self.style_manager.populate()
        # Set the default system language.
        from mailman.core.i18n import _
        _.default = self.mailman.default_language

    @property
    def logger_configs(self):
        """Return all log config sections."""
        return self._config.getByCategory('logging', [])

    @property
    def paths(self):
        """Return a substitution dictionary of all path variables."""
        return dict((k, self.__dict__[k])
                    for k in self.__dict__
                    if k.endswith('_DIR'))

    def ensure_directories_exist(self):
        """Create all path directories if they do not exist."""
        for variable, directory in self.paths.items():
            makedirs(directory)

    @property
    def qrunner_configs(self):
        """Iterate over all the qrunner configuration sections."""
        for section in self._config.getByCategory('qrunner', []):
            yield section

    @property
    def archivers(self):
        """Iterate over all the enabled archivers."""
        for section in self._config.getByCategory('archiver', []):
            if not as_boolean(section.enable):
                continue
            class_path = section['class']
            yield call_name(class_path)

    @property
    def style_configs(self):
        """Iterate over all the style configuration sections."""
        for section in self._config.getByCategory('style', []):
            yield section

    @property
    def header_matches(self):
        """Iterate over all spam matching headers.

        Values are 3-tuples of (header, pattern, chain)
        """
        matches = self._config.getByCategory('spam.headers', [])
        for match in matches:
            yield (matches.header, matches.pattern, matches.chain)
