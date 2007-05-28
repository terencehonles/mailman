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

"""Logging initialization, using Python's standard logging package.

This module cannot be called 'logging' because that would interfere with the
import below.  Ah, for Python 2.5 and absolute imports.
"""

import os
import sys
import codecs
import logging
import ConfigParser

from Mailman.configuration import config



FMT     = '%(asctime)s (%(process)d) %(message)s'
DATEFMT = '%b %d %H:%M:%S %Y'

LOGGERS = (
    'bounce',       # All bounce processing logs go here
    'config',       # Configuration issues
    'debug',        # Only used for development
    'error',        # All exceptions go to this log
    'fromusenet',   # Information related to the Usenet to Mailman gateway
    'http',         # Internal wsgi-based web interface
    'locks',        # Lock state changes
    'mischief',     # Various types of hostile activity
    'post',         # Information about messages posted to mailing lists
    'qrunner',      # qrunner start/stops
    'smtp',         # Successful SMTP activity
    'smtp-failure', # Unsuccessful SMTP activity
    'subscribe',    # Information about leaves/joins
    'vette',        # Information related to admindb activity
    )

_handlers = []



class ReallySafeConfigParser(ConfigParser.SafeConfigParser):
    def getstring(self, section, option, default=None):
        try:
            return ConfigParser.SafeConfigParser.get(self, section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def getboolean(self, section, option, default=None):
        try:
            return ConfigParser.SafeConfigParser.getboolean(
                self, section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default



class ReopenableFileHandler(logging.Handler):
    def __init__(self, filename):
        self._filename = filename
        self._stream = self._open()
        logging.Handler.__init__(self)

    def _open(self):
        return codecs.open(self._filename, 'a', 'utf-8')

    def flush(self):
        if self._stream:
            self._stream.flush()

    def emit(self, record):
        # It's possible for the stream to have been closed by the time we get
        # here, due to the shut down semantics.  This mostly happens in the
        # test suite, but be defensive anyway.
        stream = self._stream or sys.stderr
        try:
            msg = self.format(record)
            fs = '%s\n'
            try:
                stream.write(fs % msg)
            except UnicodeError:
                stream.write(fs % msg.encode('string-escape'))
            self.flush()
        except:
            self.handleError(record)

    def close(self):
        self.flush()
        self._stream.close()
        self._stream = None
        logging.Handler.close(self)

    def reopen(self):
        self._stream.close()
        self._stream = self._open()



def initialize(propagate=False):
    # Initialize the root logger, then create a formatter for all the sublogs.
    logging.basicConfig(format=FMT, datefmt=DATEFMT, level=logging.INFO)
    # If a custom log configuration file was specified, load it now.  Note
    # that we don't use logging.config.fileConfig() because it requires that
    # all loggers, formatters, and handlers be defined.  We want to support
    # minimal overloading of our logger configurations.
    cp = ReallySafeConfigParser()
    if config.LOG_CONFIG_FILE:
        path = os.path.join(config.ETC_DIR, config.LOG_CONFIG_FILE)
        cp.read(os.path.normpath(path))
    # Create the subloggers
    for logger in LOGGERS:
        log = logging.getLogger('mailman.' + logger)
        # Get settings from log configuration file (or defaults).
        log_format      = cp.getstring(logger, 'format', FMT)
        log_datefmt     = cp.getstring(logger, 'datefmt', DATEFMT)
        # Propagation to the root logger is how we handle logging to stderr
        # when the qrunners are not run as a subprocess of mailmanctl.
        log.propagate   = cp.getboolean(logger, 'propagate', propagate)
        # Set the logger's level.  Note that if the log configuration file
        # does not set an override, the default level will be INFO except for
        # the 'debug' logger.  It doesn't make much sense for the debug logger
        # to ignore debug level messages!
        level_str = cp.getstring(logger, 'level', 'INFO').upper()
        level_def = (logging.DEBUG if logger == 'debug' else logging.INFO)
        level_int = getattr(logging, level_str, level_def)
        log.setLevel(level_int)
        # Create a formatter for this logger, then a handler, and link the
        # formatter to the handler.
        formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
        path_str  = cp.getstring(logger, 'path', logger)
        path_abs  = os.path.normpath(os.path.join(config.LOG_DIR, path_str))
        handler   = ReopenableFileHandler(path_abs)
        _handlers.append(handler)
        handler.setFormatter(formatter)
        log.addHandler(handler)



def reopen():
    for handler in _handlers:
        handler.reopen()
