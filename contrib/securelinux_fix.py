#! /usr/bin/env python
#
# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Fixes for running Mailman under the `secure-linux' patch.

If you use Solar Designer's secure-linux patch, it prevents a process from
linking (hard link) to a file it doesn't own.  As a result Mailman has to be
changed so that the whole tree is owned by Mailman, and the CGIs and some of
the programs in the bin tree (the ones that lock config.db files) are SUID
Mailman.  The idea is that config.db files have to be owned by the mailman UID
and only touched by programs that are UID mailman.
 
If you have to run check_perms -f, make sure to also run %(PROGRAM) -f, which
applies the necessary permission fixes
 
As a result, to prevent anyone from running priviledged Mailman commands
\(since the scripts are suid), binary commands that are changed to be SUID are
also unreadable and unrunable by people who aren't in the mailman group.  This
shouldn't affect much since most of those commands would fail work if you
weren't part of the mailman group anyway.

Marc <marcsoft@merlins.org>/<marc_bts@valinux.com> 2000/10/27
"""

import sys
import os
import paths
import re
import glob
from Mailman import mm_cfg
from Mailman.mm_cfg import MAILMAN_UID, MAILMAN_GID
from stat import *

PROGRAM = sys.argv[0]

# Those are the programs that we patch so that they insist being run under the
# mailman uid or as root.
binfilestopatch= ( 'add_members', 'check_db', 'clone_member', 
	'config_list', 'move_list', 'newlist', 'remove_members', 'rmlist', 
	'sync_members', 'update', 'withlist' )

def main(argv):
    binpath = paths.prefix + '/bin/'
    droplib = binpath + 'CheckFixUid.py'

    if len(argv) < 2 or argv[1] != "-f":
	print __doc__
	sys.exit(1)

    if not os.path.exists(droplib):
	print "Creating " + droplib
	fp = open(droplib, 'w', 0644)
	fp.write("""import sys
import os
from Mailman.mm_cfg import MAILMAN_UID, MAILMAN_GID

class CheckFixUid:
    if os.geteuid() == 0:
	os.setgid(MAILMAN_GID)
	os.setuid(MAILMAN_UID)
    if os.geteuid() != MAILMAN_UID:
	print "You need to run this script as root or mailman because it was configured to run"
	print "on a linux system with the secure-linux patch which restricts hard links"
	sys.exit()
""")
	fp.close()
    else:
	print "Skipping creation of " + droplib


    print "\nMaking cgis setuid mailman"
    cgis = glob.glob(paths.prefix + '/cgi-bin/*')
    
    for file in cgis:
	print file
	os.chown(file, MAILMAN_UID, MAILMAN_GID)
	os.chmod(file, 06755)

    print "\nMaking mail wrapper setuid mailman"
    os.chown(paths.prefix + '/mail/wrapper', MAILMAN_UID, MAILMAN_GID)
    os.chmod(paths.prefix + '/mail/wrapper', 06755)

    print "\nEnsuring that all config.db files are owned by Mailman"
    cdbs = glob.glob(paths.prefix + '/lists/*/config.db*')

    for file in cdbs:
	stat = os.stat(file)
	if (stat[ST_UID] != MAILMAN_UID or stat[ST_GID] != MAILMAN_GID):
	    print file
	    os.chown(file, MAILMAN_UID, MAILMAN_GID)
    
    print "\nPatching mailman scripts to change the uid to mailman"

    for script in binfilestopatch:
	filefd = open(script, "r")
	file = filefd.readlines()
	filefd.close()

	patched = 0
	try:
	    file.index("import CheckFixUid\n")
	    print "Not patching " + script + ", already patched"
	except ValueError:
	    file.insert(file.index("import paths\n")+1, "import CheckFixUid\n")
	    for i in range(len(file)-1, 0, -1):
		object=re.compile("^([	 ]*)main\(").search(file[i])
		if object:
		    print "Patching " + script
		    file.insert(i, 
			object.group(1) + "CheckFixUid.CheckFixUid()\n")
		    patched=1
		    break

	    if patched==0:
		print "Warning, file "+script+" couldn't be patched."
		print "If you use it, mailman may not function properly"
	    else:
		filefd=open(script, "w")
		filefd.writelines(file)
	    
main(sys.argv)
