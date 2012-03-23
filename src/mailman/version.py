# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Mailman version strings."""

# Mailman version.
VERSION = '3.0.0b1'
CODENAME = "The Twilight Zone"

# And as a hex number in the manner of PY_VERSION_HEX.
ALPHA = 0xa
BETA  = 0xb
GAMMA = 0xc
# Release candidates.
RC    = GAMMA
FINAL = 0xf

MAJOR_REV = 3
MINOR_REV = 0
MICRO_REV = 0
REL_LEVEL = BETA
# At most 15 beta releases!
REL_SERIAL = 1

HEX_VERSION = ((MAJOR_REV << 24) | (MINOR_REV << 16) | (MICRO_REV << 8) |
               (REL_LEVEL << 4)  | (REL_SERIAL << 0))


# queue/*.pck schema version number.
QFILE_SCHEMA_VERSION = 3

# Printable version string used by command line scripts.
MAILMAN_VERSION = 'GNU Mailman ' + VERSION
MAILMAN_VERSION_FULL = MAILMAN_VERSION + ' (' + CODENAME + ')'
