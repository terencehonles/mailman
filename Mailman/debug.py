# Copyright (C) 1998 by the Free Software Foundation, Inc.
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

import sys
import os
import Utils
import traceback


# We don't use Utils.maketext() here because we want to reduce the critical
# path to getting this page vended.  Using Utils.maketext() just introduces
# another path for code that could go wrong.
def print_trace():
    print """\
Content-type: text/html

<p><h3>We're sorry, we hit a bug!</h3>

<p>If you would like to help us identify the problem, please
email a copy of this page to the webmaster for this site with
a description of what happened.  Thanks!

<p><pre>
"""
    print sys.argv
    try:
        stderr = sys.stderr
        try:
            sys.stderr = sys.stdout
            traceback.print_exc()
        finally:
            sys.stderr = stderr
    except:
        print '[failed to get a traceback]'
    print '\n\n</pre>'


# Same comment as above applies here
def print_environ():
    print '''\
<p><hr><h4>Environment variables:</h4>

<p><table>
<tr><td><strong><font size=+1>Variable</font></strong></td>
<td><strong><font size=+1>Value</font></strong></td></tr>
'''
    for varname, value in os.environ.items():
	print '<tr><td>', varname, '</td><td>', value, '</td></tr>'
    print '</table>'
