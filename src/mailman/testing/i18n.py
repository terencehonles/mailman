# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Internationalization for the tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'TestingStrategy',
    'initialize',
    ]


from contextlib import closing
from flufl.i18n import registry
from gettext import GNUTranslations, NullTranslations
from pkg_resources import resource_stream

from mailman.core.i18n import initialize as core_initialize



class TestingStrategy:
    """A strategy that finds catalogs in the testing directory."""

    def __init__(self, name):
        self.name = name

    def __call__(self, language_code=None):
        if language_code in ('en', None):
            return NullTranslations()
        mo_file = 'mailman-%s.mo' % language_code
        with closing(resource_stream('mailman.testing', mo_file)) as fp:
            return GNUTranslations(fp)



def initialize():
    """Install a global underscore function for testing purposes."""
    strategy = TestingStrategy('mailman-testing')
    application = registry.register(strategy)
    core_initialize(application)
