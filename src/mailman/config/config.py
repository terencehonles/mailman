# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Configuration',
    ]


import os
import sys

from lazr.config import ConfigSchema, as_boolean
from pkg_resources import resource_stream
from string import Template
from zope.component import getUtility
from zope.interface import Interface, implements

import mailman.templates

from mailman import version
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.styles import IStyleManager
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
        self.QFILE_SCHEMA_VERSION = version.QFILE_SCHEMA_VERSION
        self._config = None
        self.filename = None
        # Whether to create run-time paths or not.  This is for the test
        # suite, which will set this to False until the test layer is set up.
        self.create_paths = True
        # Create various registries.
        self.chains = {}
        self.rules = {}
        self.handlers = {}
        self.pipelines = {}
        self.commands = {}

    def _clear(self):
        """Clear the cached configuration variables."""
        self.switchboards.clear()
        getUtility(ILanguageManager).clear()

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
        # Expand and set up all directories.
        self._expand_paths()
        # Set up the switchboards.  Import this here to avoid circular imports.
        from mailman.core.switchboard import Switchboard
        Switchboard.initialize()
        # Set up all the languages.
        languages = self._config.getByCategory('language', [])
        language_manager = getUtility(ILanguageManager)
        for language in languages:
            if language.enabled:
                code = language.name.split('.')[1]
                language_manager.add(
                    code, language.charset, language.description)
        # The default language must always be available.
        assert self._config.mailman.default_language in language_manager, (
            'System default language code not defined: %s' %
            self._config.mailman.default_language)
        self.ensure_directories_exist()
        getUtility(IStyleManager).populate()
        # Set the default system language.
        from mailman.core.i18n import _
        _.default = self.mailman.default_language

    def _expand_paths(self):
        """Expand all configuration paths."""
        # Set up directories.
        bin_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        # Now that we've loaded all the configuration files we're going to
        # load, set up some useful directories based on the settings in the
        # configuration file.
        layout = 'paths.' + self._config.mailman.layout
        for category in self._config.getByCategory('paths'):
            if category.name == layout:
                break
        else:
            print('No path configuration found:', layout, file=sys.stderr)
            sys.exit(1)
        # First, collect all variables in a substitution dictionary.  $VAR_DIR
        # is taken from the environment or from the configuration file if the
        # environment is not set.  Because the var_dir setting in the config
        # file could be a relative path, and because 'bin/mailman start'
        # chdirs to $VAR_DIR, without this subprocesses bin/master and
        # bin/runner will create $VAR_DIR hierarchies under $VAR_DIR when that
        # path is relative.
        var_dir = os.environ.get('MAILMAN_VAR_DIR', category.var_dir)
        substitutions = dict(
            argv                    = bin_dir,
            # Directories.
            bin_dir                 = category.bin_dir,
            data_dir                = category.data_dir,
            etc_dir                 = category.etc_dir,
            ext_dir                 = category.ext_dir,
            list_data_dir           = category.list_data_dir,
            lock_dir                = category.lock_dir,
            log_dir                 = category.log_dir,
            messages_dir            = category.messages_dir,
            archive_dir             = category.archive_dir,
            queue_dir               = category.queue_dir,
            var_dir                 = var_dir,
            template_dir            = (
                os.path.dirname(mailman.templates.__file__)
                if category.template_dir == ':source:'
                else category.template_dir),
            # Files.
            lock_file               = category.lock_file,
            pid_file                = category.pid_file,
            )
        # Now, perform substitutions recursively until there are no more
        # variables with $-vars in them, or until substitutions are not
        # helping any more.
        last_dollar_count = 0
        while True:
            # Mutate the dictionary during iteration.
            dollar_count = 0
            for key in substitutions.keys():
                raw_value = substitutions[key]
                value = Template(raw_value).safe_substitute(substitutions)
                if '$' in value:
                    # Still more work to do.
                    dollar_count += 1
                substitutions[key] = value
            if dollar_count == 0:
                break
            if dollar_count == last_dollar_count:
                print('Path expansion infloop detected', file=sys.stderr)
                sys.exit(1)
            last_dollar_count = dollar_count
        # Ensure that all paths are normalized and made absolute.  Handle the
        # few special cases first.  Most of these are due to backward
        # compatibility.
        self.PID_FILE = os.path.abspath(substitutions.pop('pid_file'))
        for key in substitutions:
            attribute = key.upper()
            setattr(self, attribute, os.path.abspath(substitutions[key]))

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
        if self.create_paths:
            for variable, directory in self.paths.items():
                makedirs(directory)

    @property
    def runner_configs(self):
        """Iterate over all the runner configuration sections."""
        for section in self._config.getByCategory('runner', []):
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
