#! /usr/bin/env python
#
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

# This script is being deprecated, in favor hookups for an external archiver.

# We don't need to lock in this script, because we're never going to change
# data.

import sys
import os
import string
from Mailman import Utils, MailList, htmlformat


def ArchiveFilter(str):
    try:
        if str[:7] <> 'volume_':
            return 0
        try:
            x = int(str[7:])
        except ValueError:
            return 0
        if x < 1:
            return 0
        return 1
    except IndexError:
        return 0


def GetArchiveList(mlist):
    archive_list = htmlformat.UnorderedList()
    try:
	dir_listing = filter(ArchiveFilter, os.listdir(mlist.archive_dir()))
    except os.error:
	return "<h3><em>No archives are currently available.</em></h3>"
    if not len(dir_listing):
	return "<h3><em>No archives are currently available.</em></h3>"
    for dir in dir_listing:
	link = htmlformat.Link("%s/%s" % (mlist._base_archive_url, dir),
			       "Volume %s" % dir[7:])
	archive_list.AddItem(link)
    return archive_list.Format()
	
    
def main():
    print "Content-type: text/html"
    print

    list_info = []
    try:
        path = os.environ['PATH_INFO']
        list_info = Utils.GetPathPieces(path)
    except KeyError:
        pass

    if len(list_info) < 1:
        print "<h2>Invalid options to CGI script.</h2>"
        sys.exit(0)

    list_name = string.lower(list_info[0])
    try:
        mlist = MailList.MailList(list_name)
    except:
        print "<h2>%s: No such list.</h2>" % list_name
        sys.exit(0)

    if not mlist._ready:
        print "<h2>%s: No such list.</h2>" % list_name
        sys.exit(0)

    replacements = mlist.GetStandardReplacements()
    replacements['<mm-archive-list>'] = GetArchiveList(mlist)

    # Just doing print mlist.ParseTags(...) calls ParseTags twice???
    text = mlist.ParseTags('archives.html', replacements)
    print text
