import sys, os, string
import mm_utils, mm_mbox, mm_cfg, mm_message

## ARCHIVE_PENDING = "to-archive.mail"
## # ARCHIVE_RETAIN will be ignored, below, in our hook up with andrew's new
## # pipermail.
## ARCHIVE_RETAIN = "retained.mail"

class Archiver:
    def InitVars(self):
	# Configurable
	self.archive = 1
	# 0=public, 1=private:
	self.archive_private = mm_cfg.DEFAULT_ARCHIVE_PRIVATE
	# Though the archive file dirs are instance vars, they are not
	# settable from the web interface.  If you REALLY want to redirect
	# something to a different dir, you can set the member vars by
	# hand, from the python interpreter!
	self.public_archive_file_dir = mm_cfg.PUBLIC_ARCHIVE_FILE_DIR
	self.private_archive_file_dir = mm_cfg.PRIVATE_ARCHIVE_FILE_DIR
	self.archive_directory = os.path.join(mm_cfg.HTML_DIR, "archives/%s" % 
					      self._internal_name)
## 	self.archive_update_frequency = \
## 		 mm_cfg.DEFAULT_ARCHIVE_UPDATE_FREQUENCY
## 	self.archive_volume_frequency = \
## 		mm_cfg.DEFAULT_ARCHIVE_VOLUME_FREQUENCY
## 	self.archive_retain_text_copy = \
## 		mm_cfg.DEFAULT_ARCHIVE_RETAIN_TEXT_COPY

	# Not configurable
	# XXX klm - reconcile with .ArchiveFileName()
	self._base_archive_url = os.path.join(mm_cfg.ARCHIVE_URL, 
					      self._internal_name + ".html")
	self.clobber_date = 0

    def GetConfigInfo(self):
	return [
	    ('archive', mm_cfg.Toggle, ('No', 'Yes'), 0, 
	     'Archive messages?'),

	    ('archive_private', mm_cfg.Radio, ('public', 'private'), 0,
             'Is archive file source for public or private archival?'),

	    ('clobber_date', mm_cfg.Radio, ('When sent', 'When resent'), 0,
	     'Set date in archive to when the mail is claimed to have been '
             'sent, or to the time we resend it?'),

## 	    ('archive_update_frequency', mm_cfg.Number, 3, 0,
## 	     "How often should new messages be incorporated?  "
## 	     "0 for no archival, 1 for daily, 2 for hourly"),

## 	    ('archive_volume_frequency', mm_cfg.Radio, ('Yearly', 'Monthly'),
## 	     0,
## 	     'How often should a new archive volume be started?'),

## 	    ('archive_retain_text_copy', mm_cfg.Toggle, ('No', 'Yes'),
## 	     0,
## 	     'Retain plain text copy of archive?'),
	    ]

    def UpdateArchive(self):
	# This method is being deprecated, in favor of external archiver!
	if not self.archive:
	    return
	archive_file_name = os.path.join(self._full_path, ARCHIVE_PENDING)
	archive_dir = os.path.join(self.archive_directory, 'volume_%d' 
				   % self.volume)

	# Test to make sure there are posts to archive
	archive_file = open(archive_file_name, 'r')
	text = string.strip(archive_file.read())
	archive_file.close()
	if not text:
	    return
	mm_utils.MakeDirTree(archive_dir, 0755)
	# Pipermail 0.0.2 always looks at sys.argv, and I wasn't into hacking
	# it more than I had to, so here's a small hack to get around that,
	# calling pipermail w/ the correct options.
	real_argv = sys.argv
	sys.argv = ['pipermail', '-d%s' % archive_dir, '-l%s' % 
		    self._internal_name, '-m%s' % archive_file_name, 
		    '-s%s' % os.path.join(archive_dir, "INDEX")]

	import pipermail
	sys.argv = real_argv
	f = open(archive_file_name, 'w+')
	f.truncate(0)
	f.close()

# Internal function, don't call this.
    def ArchiveMail(self, post):
	"""Retain a text copy of the message in an mbox file."""
	if self.clobber_date:
	    import time
	    olddate = post.getheader('date')
	    post.SetHeader('Date', time.ctime(time.time()))
	try:
	    afn = self.ArchiveFileName()
	    mbox = self.ArchiveFile(afn)
	    mbox.AppendMessage(post)
	    mbox.fp.close()
	except IOError, msg:
	    self.LogMsg("error", ("Archive file access failure:\n"
				   "\t%s %s"
				   % (afn, `msg[1]`)))
	if self.clobber_date:
	    # Resurrect original date setting.
	    post.SetHeader('Date', olddate)
	self.Save ()

    def ArchiveFileName(self):
	"""The mbox name where messages are left for archive construction."""
	if self.archive_private:
	    return os.path.join(self.private_archive_file_dir,
				self._internal_name)
	else:
	    return os.path.join(self.public_archive_file_dir,
				self._internal_name)
    def ArchiveFile(self, afn):
	"""Open (creating, if necessary) the named archive file."""
	ou = os.umask(002)
	try:
	    try:
		return mm_mbox.Mailbox(open(afn, "a+"))
	    except IOError, msg:
		raise IOError, msg
	finally:
	    os.umask(ou)
	    
