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
#
# debug.py:  Utility functions for debugging.  
# Michael McLay <mclay@nist.gov> wrote print_trace().
# John Viega reconstructed print_environ since it wasn't provided...

import sys

def print_trace():
    print "Content-type: text/html\n"             
    print "<p><h3>We're sorry, we hit a bug!</h3>\n"                      
    print "If you would like to help us identify the problem, please " 
    print "email a copy of this page to the webmaster for this site"
    print 'with a description of what happened.  Thanks!'
    print "\n<PRE>"
    print sys.argv                                           
    try:                                                        
        import traceback                                                
        sys.stderr = sys.stdout
        traceback.print_exc()                                           
    except:
        print "[failed to get traceback]"                     
    print "\n\n</PRE>"   

def print_environ():
    import os
    print "<p><hr><h4>Environment variables:</h4>"
    print "<table>"
    print "<tr><td><strong><font size=+1>Variable</font></strong></td>"
    print "<td><strong><font size=+1>Value</font></strong></td></tr>"
    for (x,y) in os.environ.items():
	print "<tr><td>", x, "</td><td>", y, "</td></tr>"
    print "</table>"

