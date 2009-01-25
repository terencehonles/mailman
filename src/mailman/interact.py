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

"""Provide an interactive prompt, mimicking the Python interpreter."""

from __future__ import unicode_literals

__metaclass__ = type
__all__ = [
    'interact',
    ]

import os
import sys
import code

DEFAULT_BANNER = object()



def interact(upframe=True, banner=DEFAULT_BANNER, overrides=None):
    # The interactive prompt's namespace
    ns = dict()
    # If uplocals is true, also populate the console's locals with the locals
    # of the frame that called this function (i.e. one up from here).
    if upframe:
        frame = sys._getframe(1)
        ns.update(frame.f_globals)
        ns.update(frame.f_locals)
    if overrides is not None:
        ns.update(overrides)
    interp = code.InteractiveConsole(ns)
    # Try to import the readline module, but don't worry if it's unavailable
    try:
        import readline
    except ImportError:
        pass
    # Mimic the real interactive interpreter's loading of any $PYTHONSTARTUP
    # file.  Note that if the startup file is not prepared to be exec'd more
    # than once, this could cause a problem.
    startup = os.environ.get('PYTHONSTARTUP')
    if startup:
        try:
            execfile(startup, ns)
        except:
            pass
    # We don't want the funky console object in parentheses in the banner.
    if banner is DEFAULT_BANNER:
        banner = '''\
Python %s on %s
Type "help", "copyright", "credits" or "license" for more information.''' % (
            sys.version, sys.platform)
    elif not banner:
        banner = None
    interp.interact(banner)
    # When an exception occurs in the InteractiveConsole, the various
    # sys.exc_* attributes get set so that error handling works the same way
    # there as it does in the built-in interpreter.  Be anal about clearing
    # any exception information before we're done.
    sys.exc_clear()
    sys.last_type = sys.last_value = sys.last_traceback = None
