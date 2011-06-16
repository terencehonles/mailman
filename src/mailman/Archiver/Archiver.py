# Copyright (C) 1998-2011 by the Free Software Foundation, Inc.
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
 # USA.

"""Mixin class for putting new messages in the right place for archival.

Public archives are separated from private ones.  An external archival
mechanism (eg, pipermail) should be pointed to the right places, to do the
archival.
"""

import os
import errno
import logging
import mailbox

from cStringIO import StringIO
from string import Template
from zope.component import getUtility

from mailman.config import config
from mailman.interfaces.domain import IDomainManager
from mailman.utilities.i18n import make

log = logging.getLogger('mailman.error')



def makelink(old, new):
    try:
        os.symlink(old, new)
    except OSError, e:
        if e.errno <> errno.EEXIST:
            raise

def breaklink(link):
    try:
        os.unlink(link)
    except OSError, e:
        if e.errno <> errno.ENOENT:
            raise



class Archiver:
    #
    # Interface to Pipermail.  HyperArch.py uses this method to get the
    # archive directory for the mailing list
    #
    def InitVars(self):
        # The archive file structure by default is:
        #
        # archives/
        #     private/
        #         listname.mbox/
        #             listname.mbox
        #         listname/
        #             lots-of-pipermail-stuff
        #     public/
        #         listname.mbox@ -> ../private/listname.mbox
        #         listname@ -> ../private/listname
        #
        # IOW, the mbox and pipermail archives are always stored in the
        # private archive for the list.  This is safe because archives/private
        # is always set to o-rx.  Public archives have a symlink to get around
        # the private directory, pointing directly to the private/listname
        # which has o+rx permissions.  Private archives do not have the
        # symbolic links.
        archdir = self.archive_dir(self.fqdn_listname)
        omask = os.umask(0)
        try:
            try:
                os.mkdir(archdir+'.mbox', 02775)
            except OSError, e:
                if e.errno <> errno.EEXIST:
                    raise
                # We also create an empty pipermail archive directory into
                # which we'll drop an empty index.html file into.  This is so
                # that lists that have not yet received a posting have
                # /something/ as their index.html, and don't just get a 404.
            try:
                os.mkdir(archdir, 02775)
            except OSError, e:
                if e.errno <> errno.EEXIST:
                    raise
            # See if there's an index.html file there already and if not,
            # write in the empty archive notice.
            indexfile = os.path.join(archdir, 'index.html')
            fp = None
            try:
                fp = open(indexfile)
            except IOError, e:
                if e.errno <> errno.ENOENT:
                    raise
                omask = os.umask(002)
                try:
                    fp = open(indexfile, 'w')
                finally:
                    os.umask(omask)
                fp.write(make('emptyarchive.html',
                              mailing_list=self,
                              listname=self.real_name,
                              listinfo=self.GetScriptURL('listinfo'),
                              ))
            if fp:
                fp.close()
        finally:
            os.umask(omask)

    def ArchiveFileName(self):
        """The mbox name where messages are left for archive construction."""
        return os.path.join(self.archive_dir() + '.mbox',
                            self.fqdn_listname + '.mbox')

    def GetBaseArchiveURL(self):
        if self.archive_private:
            url = self.GetScriptURL('private') + '/index.html'
        else:
            domain = getUtility(IDomainManager).get(self.mail_host)
            web_host = (self.mail_host if domain is None else domain.url_host)
            url = Template(config.PUBLIC_ARCHIVE_URL).safe_substitute(
                listname=self.fqdn_listname,
                hostname=web_host,
                fqdn_listname=self.fqdn_listname,
                )
        return url

    def __archive_file(self, afn):
        """Open (creating, if necessary) the named archive file."""
        omask = os.umask(002)
        try:
            return mailbox.mbox(afn, 'a+')
        finally:
            os.umask(omask)

    #
    # old ArchiveMail function, retained under a new name
    # for optional archiving to an mbox
    #
    def __archive_to_mbox(self, post):
        """Retain a text copy of the message in an mbox file."""
        try:
            afn = self.ArchiveFileName()
            mbox = self.__archive_file(afn)
            mbox.add(post)
            mbox.fp.close()
        except IOError, msg:
            log.error('Archive file access failure:\n\t%s %s', afn, msg)
            raise

    def ExternalArchive(self, ar, txt):
        cmd = Template(ar).safe_substitute(
            listname=self.fqdn_listname,
            hostname=self.mail_host)
        extarch = os.popen(cmd, 'w')
        extarch.write(txt)
        status = extarch.close()
        if status:
            log.error('external archiver non-zero exit status: %d\n',
                      (status & 0xff00) >> 8)

    #
    # archiving in real time  this is called from list.post(msg)
    #
    def ArchiveMail(self, msg):
        """Store postings in mbox and/or pipermail archive, depending."""
        # Fork so archival errors won't disrupt normal list delivery
        if config.ARCHIVE_TO_MBOX == -1:
            return
        #
        # We don't need an extra archiver lock here because we know the list
        # itself must be locked.
        if config.ARCHIVE_TO_MBOX in (1, 2):
            self.__archive_to_mbox(msg)
            if config.ARCHIVE_TO_MBOX == 1:
                # Archive to mbox only.
                return
        txt = str(msg)
        # should we use the internal or external archiver?
        private_p = self.archive_private
        if config.PUBLIC_EXTERNAL_ARCHIVER and not private_p:
            self.ExternalArchive(config.PUBLIC_EXTERNAL_ARCHIVER, txt)
        elif config.PRIVATE_EXTERNAL_ARCHIVER and private_p:
            self.ExternalArchive(config.PRIVATE_EXTERNAL_ARCHIVER, txt)
        else:
            # use the internal archiver
            f = StringIO(txt)
            import HyperArch
            h = HyperArch.HyperArchive(self)
            h.processUnixMailbox(f)
            h.close()
            f.close()

    #
    # called from MailList.MailList.Save()
    #
    def CheckHTMLArchiveDir(self):
        # We need to make sure that the archive directory has the right perms
        # for public vs private.  If it doesn't exist, or some weird
        # permissions errors prevent us from stating the directory, it's
        # pointless to try to fix the perms, so we just return -scott
        if config.ARCHIVE_TO_MBOX == -1:
            # Archiving is completely disabled, don't require the skeleton.
            return
        pubdir = os.path.join(config.PUBLIC_ARCHIVE_FILE_DIR,
                              self.fqdn_listname)
        privdir = self.archive_dir()
        pubmbox = pubdir + '.mbox'
        privmbox = privdir + '.mbox'
        if self.archive_private:
            breaklink(pubdir)
            breaklink(pubmbox)
        else:
            # BAW: privdir or privmbox could be nonexistant.  We'd get an
            # OSError, ENOENT which should be caught and reported properly.
            makelink(privdir, pubdir)
            # Only make this link if the site has enabled public mbox files
            if config.PUBLIC_MBOX:
                makelink(privmbox, pubmbox)
