#! @PYTHON@
#
# Copyright (C) 1998-2006 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

import os
import sys
import optparse

try:
    import gzip
except ImportError:
    sys.exit(0)

from Mailman import MailList
from Mailman import Utils
from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [listname ...]

Re-generate the Pipermail gzip'd archive flat files."""))
    parser.add_option('-v', '--verbose',
                      default=False, action='store_true',
                      help=_("Print each file as it's being gzip'd"))
    parser.add_option('-z', '--level',
                      default=6, type='int',
                      help=_('Specifies the compression level'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if opts.level < 1 or opts.level > 9:
        parser.print_help()
        print >> sys.stderr, _('Illegal compression level: $opts.level')
        sys.exit(1)
    return opts, args, parser



def compress(txtfile, opts):
    if opts.verbose:
        print _("gzip'ing: $txtfile")
    infp = outfp = None
    try:
        infp = open(txtfile)
        outfp = gzip.open(txtfile + '.gz', 'wb', opts.level)
        outfp.write(infp.read())
    finally:
        if outfp:
            outfp.close()
        if infp:
            infp.close()



def main():
    opts, args, parser = parseargs()
    config.load(opts.config)

    if config.ARCHIVE_TO_MBOX not in (1, 2) or config.GZIP_ARCHIVE_TXT_FILES:
        # We're only going to run the nightly archiver if messages are
        # archived to the mbox, and the gzip file is not created on demand
        # (i.e. for every individual post).  This is the normal mode of
        # operation.
        return

    # Process all the specified lists
    for listname in set(args or Utils.list_names()):
        mlist = MailList.MailList(listname, lock=False)
        if not mlist.archive:
            continue
        dir = mlist.archive_dir()
        try:
            allfiles = os.listdir(dir)
        except OSError:
            # Has the list received any messages?  If not, last_post_time will
            # be zero, so it's not really a bogus archive dir.
            if mlist.last_post_time > 0:
                print _('List $listname has a bogus archive_directory: $dir')
            continue
        if opts.verbose:
            print _('Processing list: $listname')
        files = []
        for f in allfiles:
            if os.path.splitext(f)[1] <> '.txt':
                continue
            # stat both the .txt and .txt.gz files and append them only if
            # the former is newer than the latter.
            txtfile = os.path.join(dir, f)
            gzpfile = txtfile + '.gz'
            txt_mtime = os.path.getmtime(txtfile)
            try:
                gzp_mtime = os.path.getmtime(gzpfile)
            except OSError:
                gzp_mtime = -1
            if txt_mtime > gzp_mtime:
                files.append(txtfile)
        for f in files:
            compress(f, opts)



if __name__ == '__main__':
    omask = os.umask(002)
    try:
        main()
    finally:
        os.umask(omask)
