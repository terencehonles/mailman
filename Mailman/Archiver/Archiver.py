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


"""Mixin class for putting new messages in the right place for archival.

Public archives are separated from private ones.  An external archival
mechanism (eg, pipermail) should be pointed to the right places, to do the
archival.
"""

import os
import string
import time
import errno
import traceback

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Mailbox
from Mailman import LockFile
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO



def makelink(old, new):
    try:
        os.symlink(old, new)
    except os.error, e:
        code, msg = e
        if code <> errno.EEXIST:
            raise

def breaklink(link):
    try:
        os.unlink(link)
    except os.error, e:
        code, msg = e
        if code <> errno.ENOENT:
            raise



class Archiver:
    #
    # Interface to Pipermail.  HyperArch.py uses this method to get the
    # archive directory for the mailing list
    #
    def archive_dir(self):
        return self.archive_directory

    def InitVars(self):
	# Configurable
	self.archive = 1
	# 0=public, 1=private:
	self.archive_private = mm_cfg.DEFAULT_ARCHIVE_PRIVATE
 	self.archive_volume_frequency = \
 		mm_cfg.DEFAULT_ARCHIVE_VOLUME_FREQUENCY

	# Not configurable
	self.clobber_date = 0
	# Though the archive file dirs are list-specific, they are not
	# settable from the web interface.  If you REALLY want to redirect
	# something to a different dir, you can set the member vars by
	# hand, from the Python interpreter!
        #
        # The archive file structure by default is:
        #
        # archives/
        #     private/
        #         listname.mbox/
        #             listname
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

	self.public_archive_file_dir = mm_cfg.PUBLIC_ARCHIVE_FILE_DIR
	self.private_archive_file_dir = os.path.join(
            mm_cfg.PRIVATE_ARCHIVE_FILE_DIR,
            self._internal_name + '.mbox')
	self.archive_directory = os.path.join(
            mm_cfg.PRIVATE_ARCHIVE_FILE_DIR,
            self._internal_name)
        try:
            Utils.mkdir(self.private_archive_file_dir)
        except os.error, e:
            code, msg = e
            if code <> errno.EEXIST:
                raise

    def GetBaseArchiveURL(self):
        if self.archive_private:
            return "%s%s/%s/" % (mm_cfg.PRIVATE_ARCHIVE_URL,
                                 mm_cfg.CGIEXT,
                                 self._internal_name)
        else:
            return "%s/%s/" % (mm_cfg.PUBLIC_ARCHIVE_URL, self._internal_name)

    def GetConfigInfo(self):
	return [
            "List traffic archival policies.",

	    ('archive', mm_cfg.Toggle, ('No', 'Yes'), 0, 
	     'Archive messages?'),

	    ('archive_private', mm_cfg.Radio, ('public', 'private'), 0,
             'Is archive file source for public or private archival?'),

	    ('clobber_date', mm_cfg.Radio, ('When sent', 'When resent'), 0,
	     'Set date in archive to when the mail is claimed to have been '
             'sent, or to the time we resend it?'),

 	    ('archive_volume_frequency', mm_cfg.Radio, 
               ('Yearly', 'Monthly','Quarterly', 'Weekly', 'Daily'), 0,
 	     'How often should a new archive volume be started?'),
	    ]

    def ArchiveFileName(self):
	"""The mbox name where messages are left for archive construction."""
        return os.path.join(self.private_archive_file_dir,
                            self._internal_name + '.mbox')

    def __archive_file(self, afn):
	"""Open (creating, if necessary) the named archive file."""
        from Mailman.Utils import open_ex
        return Mailbox.Mailbox(open_ex(afn, "a+"))

    #
    # old ArchiveMail function, retained under a new name
    # for optional archiving to an mbox
    #
    def __archive_to_mbox(self, post):
        """Retain a text copy of the message in an mbox file."""
        if self.clobber_date:
            olddate = post.getheader('date')
            post['Date'] = time.ctime(time.time())
        try:
            try:
                afn = self.ArchiveFileName()
                mbox = self.__archive_file(afn)
                mbox.AppendMessage(post)
                mbox.fp.close()
            except IOError, msg:
                syslog('error', 'Archive file access failure:\n\t%s %s' %
                       (afn, msg))
                raise
        finally:
            if self.clobber_date:
                # Resurrect original date setting.
                post['Date'] = olddate

    def ExternalArchive(self, ar, txt):
        d = Utils.SafeDict({'listname': self.internal_name()})
        cmd = ar % d
        extarch = os.popen(cmd, 'w')
        extarch.write(txt)
        status = extarch.close()
        if status:
            syslog('error', 'external archiver non-zero exit status: %d\n' %
                   (status & 0xff00) >> 8)

    #
    # archiving in real time  this is called from list.post(msg)
    #
    def ArchiveMail(self, msg, msgdata):
        """Store postings in mbox and/or pipermail archive, depending."""
	# Fork so archival errors won't disrupt normal list delivery
        if mm_cfg.ARCHIVE_TO_MBOX == -1:
            return
        #
        # We don't need an extra archiver lock here because we know the list
        # itself must be locked.
        if mm_cfg.ARCHIVE_TO_MBOX in (1, 2):
            self.__archive_to_mbox(msg)
            if mm_cfg.ARCHIVE_TO_MBOX == 1:
                # Archive to mbox only.
                return
        # From this point on, we're doing all the expensive archiving work.
        # If anything goes wrong here, we will simply log this and let the
        # normal delivery mechanism continue.  The archiver is too f*cked up
        # anyway, and at the very least we've got the mbox to regenerate
        # from.
        t0 = time.time()
##        syslog('error', 'starting to archive')
        try:
            txt = msg.unixfrom
            for h in msg.headers:
                txt = txt + h
            if not msg.body or msg.body[0] <> '\n':
                txt = txt + "\n"
            for line in string.split(msg.body, '\n'):
                # Quote unprotected From_ lines appearing in body
                if line and line[:5] == 'From ':
                    line = '>' + line
                txt = txt + "%s\n" % line
            # should we use the internal or external archiver?
            private_p = self.archive_private
            if mm_cfg.PUBLIC_EXTERNAL_ARCHIVER and not private_p:
                self.ExternalArchive(mm_cfg.PUBLIC_EXTERNAL_ARCHIVER, txt)
            elif mm_cfg.PRIVATE_EXTERNAL_ARCHIVER and private_p:
                self.ExternalArchive(mm_cfg.PRIVATE_EXTERNAL_ARCHIVER, txt)
            else:
                # use the internal archiver
                f = StringIO(txt)
                import HyperArch
                h = HyperArch.HyperArchive(self)
                h.processUnixMailbox(f, HyperArch.Article)
                h.close()
                f.close()
        except:
            traceback.print_exc()
            syslog('error', 'CORRUPT ARCHIVE FOR LIST: %s' %
                   self.internal_name())
        else:
            t1 = time.time()
##            syslog('error', 'finished archiving in %.3f seconds' % (t1-t0))
	
    #
    # called from MailList.MailList.Save()
    #
    def CheckHTMLArchiveDir(self):
        #
        # we need to make sure that the archive
        # directory has the right perms for public vs
        # private.  If it doesn't exist, or some weird
        # permissions errors prevent us from stating
        # the directory, it's pointless to try to
        # fix the perms, so we just return  -scott
        #
        if mm_cfg.ARCHIVE_TO_MBOX == -1:
            # Archiving is completely disabled, don't require the skeleton.
            return
        pubdir  = os.path.join(self.public_archive_file_dir,
                               self._internal_name)
        privdir = self.archive_directory
        pubmbox = os.path.join(self.public_archive_file_dir,
                               self._internal_name + '.mbox')
        privmbox = self.archive_directory + '.mbox'
        if self.archive_private:
            breaklink(pubdir)
            breaklink(pubmbox)
        else:
            makelink(privdir, pubdir)
            makelink(privmbox, pubmbox)
