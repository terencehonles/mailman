import sys
import rfc822, string, time


# A utility function 2 of these classes use:
def AddBackNewline(str):
    return str + '\n'
	

# If we're trying to create a message object from text, we need to pass
# a file object to rfc822.Message to get it to do its magic.  Well,
# to avoid writing text out to a file, and having it read back in,
# here we define a class that will fool rfc822 into thinking it's a non-seekable
# message.
# The only method rfc822.Message ever calls on a non-seekable file is
# readline.  It doesn't use the optional arg to readline, either.
# In my subclasses, I use the read() method, and might just use readlines() 
# someday.
#
# It might be useful to expand this into a full blown fully functional class.

class FakeFile:
    def __init__(self, text):
	self.lines = map(AddBackNewline, string.split(text, '\n'))
	self.curline = 0
	self.lastline = len(self.lines) - 1
    def readline(self):
	if self.curline > self.lastline:
	    return ''
	self.curline = self.curline + 1
	return self.lines[self.curline - 1]
    def read(self):
	startline = self.curline
	self.curline = self.lastline + 1
	return string.join(self.lines[startline:], '')
    def readlines(self):
	startline = self.curline
	self.curline = self.lastline + 1
	return self.lines[startline:]
    

# We know the message is gonna come in on stdin or from text for our purposes.
class IncomingMessage(rfc822.Message):
    def __init__(self, text=None):
	if not text:
	    rfc822.Message.__init__(self, sys.stdin, 0)
	    self.body = self.fp.read()
	else:
	    rfc822.Message.__init__(self, FakeFile(text), 0)
	    self.body = self.fp.read()

    def GetSender(self):
	# Look for a Sender field.
	sender = self.getheader('sender')
	if sender:
	    realname, mail_address = self.getaddr('sender')
	else:
	    try:
		realname, mail_address = self.getaddr('from')
	    except:
		# The unix from line is all we have left...
		if self.unixfrom:
		    return string.lower(string.split(self.unixfrom)[1])

	return string.lower(mail_address)

    def GetSenderName(self):
	real_name, mail_addr = self.getaddr('from')
	if not real_name:
	    return self.GetSender()
	return real_name

    def SetHeader(self, name, value, crush_duplicates=1):
	# Well, we crush dups in the dict no matter what...
	name = "%s%s" % (name[0], name[1:])
	self.dict[string.lower(name)] = value
	if value[-1] <> '\n':
	    value = value + '\n'

	if not crush_duplicates:
	    self.headers.append('%s: %s' % (name, value))
	    return
	for i in range(len(self.headers)):
	    if (string.lower(self.headers[i][:len(name)+1]) == 
		string.lower(name) + ':'):
		self.headers[i] = '%s: %s' % (name, value)
		
# This is a simplistic class.  It could do multi-line headers etc...
# But it doesn't because I don't need that for this app.
class OutgoingMessage:
    def __init__(self, headers=None, body='', sender=None):
        self.cached_headers = {}
	if headers:
	    self.SetHeaders(headers)
	else:
	    self.headers = []
	self.body = body
	self.sender = sender

    def SetHeaders(self, headers):
	self.headers = map(AddBackNewline, string.split(headers, '\n'))

	def CacheHeaders(header, s=self):
	    i = string.find(header, ':')
	    s.cached_headers[string.lower(string.strip(header[:i]))] = \
								     header[i+2:]
	map(CacheHeaders, self.headers)

    def SetHeader(self, header, value, crush_duplicates=1):
	if value[-1] <> '\n':
	    value = value + '\n'
	if crush_duplicates:
	    # Run through the list and make sure the header isn't already there.
	    remove_these = []
	    for item in self.headers:
		f = string.find(item, ':')
		if string.lower(item[:f]) == string.lower(header):
		    remove_these.append(item)
	    for item in remove_these:
		self.headers.remove(item)
	    del remove_these
	self.headers.append('%s%s: %s' % (string.upper(header[0]),
					  string.lower(header[1:]),
					  value))
	self.cached_headers[string.lower(header)] = value

    def SetBody(self, body):
	self.body = body

    def AppendToBody(self, text):
	self.body = self.body + text

    def SetSender(self, sender, set_from=1):
        self.sender = sender
	if not self.getheader('from') and set_from:
	    self.SetHeader('from', sender)

    def SetDate(self, date=time.ctime(time.time())):
	self.SetHeader('date', date)

    def GetSender(self):
	return self.sender

# Lower case the name to give it the same UI as IncomingMessage 
# inherits from rfc822
    def getheader(self, str):
	str = string.lower(str)
	if not self.cached_headers.has_key(str):
	    return None
	return self.cached_headers[str]
