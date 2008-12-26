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

"""Logging initialization, using Python's standard logging package."""

from __future__ import absolute_import

__metaclass__ = type
__all__ = [
    'initialize',
    'reopen',
    ]


import os
import sys
import codecs
import logging
import ConfigParser

from lazr.config import as_boolean, as_log_level

from mailman.config import config


_handlers = []



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
        stream = (self._stream if self._stream else sys.stderr)
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



def initialize(propagate=None):
    """Initialize all logs.

    :param propagate: Flag specifying whether logs should propagate their
        messages to the root logger.  If omitted, propagation is determined
        from the configuration files.
    :type propagate: bool or None
    """
    # First, find the root logger and configure the logging subsystem.
    # Initialize the root logger, then create a formatter for all the
    # sublogs.  The root logger should log to stderr.
    logging.basicConfig(format=config.logging.root.format,
                        datefmt=config.logging.root.datefmt,
                        level=as_log_level(config.logging.root.level),
                        stream=sys.stderr)
    # Create the subloggers.
    for logger_config in config.logger_configs:
        sub_name = logger_config.name.split('.')[-1]
        if sub_name == 'root':
            continue
        logger_name = 'mailman.' + sub_name
        log = logging.getLogger(logger_name)
        # Get settings from log configuration file (or defaults).
        log_format      = logger_config.format
        log_datefmt     = logger_config.datefmt
        # Propagation to the root logger is how we handle logging to stderr
        # when the qrunners are not run as a subprocess of mailmanctl.
        log.propagate   = (as_boolean(logger_config.propagate)
                           if propagate is None else propagate)
        # Set the logger's level.
        log.setLevel(as_log_level(logger_config.level))
        # Create a formatter for this logger, then a handler, and link the
        # formatter to the handler.
        formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
        path_str  = logger_config.path
        path_abs  = os.path.normpath(os.path.join(config.LOG_DIR, path_str))
        handler   = ReopenableFileHandler(path_abs)
        _handlers.append(handler)
        handler.setFormatter(formatter)
        log.addHandler(handler)



def reopen():
    """Re-open all log files."""
    for handler in _handlers:
        handler.reopen()
