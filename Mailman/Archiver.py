import sys, os, string
import mm_utils, mm_mbox, mm_cfg, mm_message

class Archiver:
    def InitVars(self):
	# Configurable
	self.archive = 1
	self.archive_directory = os.path.join(mm_cfg.HTML_DIR, "archives/%s" % 
					      self._internal_name)
	# Not configurable
	self._base_archive_url = os.path.join(mm_cfg.ARCHIVE_URL, 
					      self._internal_name)
	self.archive_update_frequency = 1  # 0 = never, 1 = daily, 2 = hourly
	self.archive_volume_frequency = 0  # 0 = yearly, 1 = monthly
	self.clobber_date = 0

    def GetConfigInfo(self):
	return [
	    ('archive', mm_cfg.Toggle, ('No', 'Yes'), 0, 
	     'Archive messages?'),

	    ('archive_update_frequency', mm_cfg.Number, 3, 0,
	     "How often should new messages be incorporated?  "
	     "0 for no archival, typically 1 for daily, 2 for hourly"),

	    ('archive_volume_frequency', mm_cfg.Radio, ('Yearly', 'Monthly'),
	     0,
	     'How often should a new archive volume be started?'),

	    ('clobber_date', mm_cfg.Radio, ('When sent', 'When resent'), 0,
	     'Set date in archive to when the mail is claimed to have been '
             'sent, or to the time we resend it?'),

	    ('archive_directory', mm_cfg.String, 40, 0,
	     'Where on the machine the list archives are kept')
	    ]

    def UpdateArchive(self):
	if not self.archive:
	    return
	archive_file_name = os.path.join(self._full_path, "archived.mail")
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
	archive_file = open(os.path.join(self._full_path,
					 "archived.mail"),
			    "a+")
	archive_mbox = mm_mbox.Mailbox(archive_file)
	if self.clobber_date:
	    import time
	    olddate = post.getheader('date')
	    post.SetHeader('Date', time.ctime(time.time()))
	archive_mbox.AppendMessage(post)
	if self.clobber_date:
	    post.SetHeader('Date', olddate)
	archive_mbox.fp.close()
	self.Save ()
