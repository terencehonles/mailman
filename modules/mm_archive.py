import sys, os, string
import mm_utils, mm_mbox, mm_cfg, mm_message

ARCHIVE_PENDING = "to-archive.mail"
ARCHIVE_RETAIN = "retained.mail"

class Archiver:
    def InitVars(self):
	# Configurable
	self.archive = 1
	self.archive_directory = os.path.join(mm_cfg.HTML_DIR, "archives/%s" % 
					      self._internal_name)
	self.archive_update_frequency = \
		 mm_cfg.DEFAULT_ARCHIVE_UPDATE_FREQUENCY
	self.archive_volume_frequency = \
		mm_cfg.DEFAULT_ARCHIVE_VOLUME_FREQUENCY
	self.archive_retain_text_copy = \
		mm_cfg.DEFAULT_ARCHIVE_RETAIN_TEXT_COPY

	# Not configurable
	self._base_archive_url = os.path.join(mm_cfg.ARCHIVE_URL, 
					      self._internal_name)
	self.clobber_date = 0

    def GetConfigInfo(self):
	return [
	    ('archive', mm_cfg.Toggle, ('No', 'Yes'), 0, 
	     'Archive messages?'),

	    ('archive_update_frequency', mm_cfg.Number, 3, 0,
	     "How often should new messages be incorporated?  "
	     "0 for no archival, 1 for daily, 2 for hourly"),

	    ('archive_volume_frequency', mm_cfg.Radio, ('Yearly', 'Monthly'),
	     0,
	     'How often should a new archive volume be started?'),

	    ('archive_retain_text_copy', mm_cfg.Toggle, ('No', 'Yes'),
	     0,
	     'Retain plain text copy of archive?'),

	    ('clobber_date', mm_cfg.Radio, ('When sent', 'When resent'), 0,
	     'Set date in archive to when the mail is claimed to have been '
             'sent, or to the time we resend it?'),

	    ('archive_directory', mm_cfg.String, 40, 0,
	     'Where on the machine the list archives are kept')
	    ]

    def UpdateArchive(self):
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
	if self.clobber_date:
	    import time
	    olddate = post.getheader('date')
	    post.SetHeader('Date', time.ctime(time.time()))
	self.ArchiveMailFiler(post, ARCHIVE_PENDING)
	if self.archive_retain_text_copy:
	    self.ArchiveMailFiler(post, ARCHIVE_RETAIN)
	if self.clobber_date:
	    # Resurrect original date setting.
	    post.SetHeader('Date', olddate)
	self.Save ()

    def ArchiveMailFiler(self, post, fn):
	"""ArchiveMail helper - given file name, actually do the save."""
	mbox = mm_mbox.Mailbox(open(os.path.join(self._full_path, fn),
				    "a+"))
	mbox.AppendMessage(post)
	mbox.fp.close()
