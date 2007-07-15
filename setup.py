# Copyright (C) 2007 Barry A. Warsaw
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place - Suite 330, Boston, MA 02111-1307, USA.

import ez_setup
ez_setup.use_setuptools()

import sys

from Mailman.Version import VERSION as __version__
from setuptools import setup, find_packages



if sys.hexversion < 0x20500f0:
    print 'replybot requires at least Python 2.5'
    sys.exit(1)



scripts = ['%(script)s = Mailman.bin.%(script)s:main' % dict(script=script)
           for script in (
               'make_instance',
               'testall',
               'withlist',
               )
           ]



setup(
    name            = 'mailman',
    version         = __version__,
    description     = 'Mailman -- the GNU mailing list manager',
    long_description= """\
This is GNU Mailman, a mailing list management system distributed under the
terms of the GNU General Public License (GPL).  The name of this software is
spelled 'Mailman' with a leading capital 'M' but with a lower case second `m'.
Any other spelling is incorrect.""",
    author          = 'The Mailman Developers',
    author_email    = 'mailman-developers@python.org',
    license         = 'GPL',
    url             = 'http://www.list.org',
    keywords        = 'email',
    packages        = find_packages(),
    # Executable scripts
    entry_points    = {
        'console_scripts': scripts,
        },
    # Third-party requirements.
    install_requires = [
        'Elixir',
        'SQLAlchemy',
        'munepy',
        'wsgiref',
        'zope.interface',
        ],
    # Optionally use 'nose' for unit test sniffing.
    extras_require  = {
        'nose': ['nose'],
        },
    test_suite      = 'nose.collector',
    )
