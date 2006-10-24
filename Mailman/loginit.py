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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Logging initialization, using Python's standard logging package.

This module cannot be called 'logging' because that would interfere with the
import below.  Ah, for Python 2.5 and absolute imports.
"""

import os
import codecs
import logging

from Mailman.configuration import config

FMT     = '%(asctime)s (%(process)d) %(message)s'
DATEFMT = '%b %d %H:%M:%S %Y'
LOGGERS = (
    'bounce',
    'config',
    'debug',
    'error',
    'fromusenet',
    'http',
    'locks',
    'mischief',
    'post',
    'qrunner',
    'smtp',
    'smtp-failure',
    'subscribe',
    'vette',
    )

_handlers = []



class ReopenableFileHandler(logging.Handler):
    def __init__(self, filename):
        self._filename = filename
        self._stream = self._open()
        logging.Handler.__init__(self)

    def _open(self):
        return codecs.open(self._filename, 'a', 'utf-8')

    def flush(self):
        self._stream.flush()

    def emit(self, record):
        try:
            msg = self.format(record)
            fs = '%s\n'
            try:
                self._stream.write(fs % msg)
            except UnicodeError:
                self._stream.write(fs % msg.encode('string-escape'))
            self.flush()
        except:
            self.handleError(record)

    def close(self):
        self.flush()
        self._stream.close()
        logging.Handler.close(self)

    def reopen(self):
        self._stream.close()
        self._stream = self._open()



def initialize(propagate=False):
    # XXX Don't call logging.basicConfig() because in Python 2.3, it adds a
    # handler to the root logger that we don't want.  When Python 2.4 is the
    # minimum requirement, we can use basicConfig() with keyword arguments.
    #
    # The current set of Mailman logs are:
    #
    # error         - All exceptions go to this log
    # bounce        - All bounce processing logs go here
    # mischief      - Various types of hostile activity
    # post          - Information about messages posted to mailing lists
    # vette         - Information related to admindb activity
    # smtp          - Successful SMTP activity
    # smtp-failure  - Unsuccessful SMTP activity
    # subscribe     - Information about leaves/joins
    # config        - Configuration issues
    # locks         - Lock steals
    # qrunner       - qrunner start/stops
    # fromusenet    - Information related to the Usenet to Mailman gateway
    #
    # There was also a 'debug' logger, but that was mostly unused, so instead
    # we'll use debug level on existing loggers.
    #
    # Start by creating a common formatter and the root logger.
    formatter = logging.Formatter(fmt=FMT, datefmt=DATEFMT)
    log = logging.getLogger('mailman')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    # Create the subloggers
    for logger in LOGGERS:
        log = logging.getLogger('mailman.' + logger)
        # Propagation to the root logger is how we handle logging to stderr
        # when the qrunners are not run as a subprocess of mailmanctl.
        log.propagate = propagate
        handler = ReopenableFileHandler(os.path.join(config.LOG_DIR, logger))
        _handlers.append(handler)
        handler.setFormatter(formatter)
        log.addHandler(handler)



def reopen():
    for handler in _handlers:
        handler.reopen()
