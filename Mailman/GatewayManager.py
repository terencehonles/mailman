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

'''Mixin class for gatewaying mail to news, and news to mail.'''


# XXX: This should be integrated with the Errors module
ImproperNNTPConfigError = "ImproperNNTPConfigError"


class GatewayManager:
  def InitVars(self):
    # Configurable
    self.nntp_host        = ''
    self.linked_newsgroup = ''
    self.gateway_to_news  = 0
    self.gateway_to_mail  = 0

  def GetConfigInfo(self):
    import mm_cfg
    return [
	'Mail to news and news to mail gateway services.',
        ('nntp_host', mm_cfg.String, 50, 0,
	 'The internet address of the machine your news server is running on.',

         'The news server is not part of Mailman proper.  You have to already'
         ' have access to a nntp server, and that nntp server has to recognize'
         ' the machine this mailing list runs on as a machine capable of'
         ' reading and posting news.'),
        ('linked_newsgroup', mm_cfg.String, 50, 0,
          'The name of the usenet group to gateway to and/or from.'),
        ('gateway_to_news',  mm_cfg.Toggle, ('No', 'Yes'), 0,
	 'Should posts to the mailing list be resent to the newsgroup?'),
        ('gateway_to_mail',  mm_cfg.Toggle, ('No', 'Yes'), 0,
	 'Should newsgroup posts not sent from the list be resent to the'
         ' list?')
        ]

  # Watermarks are kept externally to avoid locking problems.
  def PollNewsGroup(self, watermark):
	if (not self.gateway_to_mail or not self.nntp_host or 
	    not self.linked_newsgroup):
	    return 0
	import nntplib, os, string, mm_cfg
	con = nntplib.NNTP(self.nntp_host)
	r,c,f,l,n = con.group(self.linked_newsgroup)
	# NEWNEWS is not portable and has synchronization issues...
	# Use a watermark system instead.
	if watermark == 0:
	  return eval(l)
	for num in range(max(watermark+1, eval(f)), eval(l)+1):
	  try:
	    headers = con.head(`num`)[3]
	    found_to = 0
            for header in headers:
	      i = string.find(header, ':')
    	      if i > 0 and string.lower(header[:i]) == 'to':
	        found_to = 1
	      if header[:i] <> 'X-BeenThere':
	        continue
	      if header[i:] == ': %s' % self.GetListEmail():
	        raise "QuickEscape"
	    body    = con.body(`num`)[3]
  	    file = os.popen("%s %s nonews" % 
	                        (os.path.join(mm_cfg.SCRIPTS_DIR,
	                        "post"), self._internal_name), "w")
	    file.write(string.join(headers,'\n'))
	    # If there wasn't already a TO: header, add one.
            if not found_to:
	      file.write("\nTo: %s" % self.GetListEmail())
	    file.write('\n\n')
	    file.write(string.join(body,'\n'))
	    file.write('\n')
	    file.close()
	  except nntplib.error_temp:
	    pass # Probably canceled, etc...        
          except "QuickEscape":
	    pass # We gated this TO news, don't repost it!
 	return eval(l)
				
  def SendMailToNewsGroup(self, mail_msg):
	import Message
	import os
	#if self.gateway_to_news == 0:
	#  return
	if self.linked_newsgroup == '' or self.nntp_host == '':
	  raise ImproperNNTPConfigError
	try:
  	  if self.tmp_prevent_gate:
	     return
        except AttributeError:
	  pass # Wasn't remailed by the news gater then.  Let it through.
	# Fork in case the nntp connection hangs.
	x = os.fork()
	if not x:
	  # Now make the news message...
	  msg = Message.NewsMessage(mail_msg)

  	  import nntplib,string

	  # Ok, munge headers, etc.
	  subj = msg.getheader('subject')
  	  if not subj:
	    msg.SetHeader('Subject', '%s(no subject)' % prefix)
  	  if self.reply_goes_to_list:
            del msg['reply-to']
            msg.headers.append('Reply-To: %s\n' % self.GetListEmail())
	  msg.headers.append('Sender: %s\n' % self.GetAdminEmail())
	  msg.headers.append('Errors-To: %s\n' % self.GetAdminEmail())
	  msg.headers.append('X-BeenThere: %s\n' % self.GetListEmail())
   	  msg.headers.append('Newsgroups: %s\n' % self.linked_newsgroup)
	  # Note:  Need to be sure 2 messages aren't ever sent to the same
          # list in the same process, since message ID's need to be unique.
          # could make the ID be mm.listname.postnum instead if that happens
	  if msg.getheader('Message-ID') == None:
	    import time
	    msg.headers.append('Message-ID: <mm.%s.%s@%s>\n' %
                (time.time(), os.getpid(), self.host_name))
	  if msg.getheader('Lines') == None:
	    msg.headers.append('Lines: %s\n' % 
                                   len(string.split(msg.body,"\n")))
	  del msg['received']

	  # NNTP is strict about spaces after the colon in headers.
          for n in range(len(msg.headers)):
	    line = msg.headers[n]
	    i = string.find(line,":")
	    if i <> -1 and line[i+1] <> ' ':
	      msg.headers[n] = line[:i+1] + ' ' + line[i+1:]
	  con = nntplib.NNTP(self.nntp_host)
   	  con.post(msg)
	  con.quit()
	  os._exit(0)
