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
from string import Template

import Mailman.bin
from Mailman.Version import VERSION as __version__
from setuptools import setup, find_packages



if sys.hexversion < 0x20500f0:
    print 'Mailman requires at least Python 2.5'
    sys.exit(1)



# Ensure that all the .mo files are generated from the corresponding .po file.
# This procedure needs to be made sane, probably when the language packs are
# properly split out.

import os
import Mailman.messages

start_dir = os.path.dirname(Mailman.messages.__file__)
for dirpath, dirnames, filenames in os.walk(start_dir):
    for filename in filenames:
        po_file = os.path.join(dirpath, filename)
        basename, ext = os.path.splitext(po_file)
        if ext <> '.po':
            continue
        mo_file = basename + '.mo'
        if (not os.path.exists(mo_file) or
            os.path.getmtime(po_file) > os.path.getmtime(mo_file)):
            # The mo file doesn't exist or is older than the po file.
            os.system('bin/msgfmt.py -o %s %s' % (mo_file, po_file))



# XXX The 'bin/' prefix here should be configurable.
template = Template('bin/$script = Mailman.bin.$script:main')
scripts = set(
    template.substitute(script=os.path.splitext(script)[0])
    for script in Mailman.bin.__all__
    if not script.startswith('_')
    )



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
    include_package_data = True,
    entry_points    = {
        'console_scripts': list(scripts),
        'setuptools.file_finders': [
            'bzr = setuptoolsbzr:find_files_for_bzr',
            ],
        },
    # Third-party requirements.
    install_requires = [
        'Elixir',
        'SQLAlchemy',
        'munepy',
        'wsgiref',
        'zope.interface',
        ],
    setup_requires = [
        'setuptoolsbzr',
        ],
    )
