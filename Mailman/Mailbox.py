"Extend mailbox.UnixMailbox."

__version__ = "$Revision: 399 $"


import mailbox

class Mailbox(mailbox.UnixMailbox):
    # msg should be an rfc822 message or a subclass.
    def AppendMessage(self, msg):
	# seek to the last char of the mailbox
	self.fp.seek(1,2)
	if self.fp.read(1) <> '\n':
	    self.fp.write('\n')
	self.fp.write(msg.unixfrom)
	for line in msg.headers:
	    self.fp.write(line)
	if msg.body[0] <> '\n':
	    self.fp.write('\n') 
	self.fp.write(msg.body)
	
