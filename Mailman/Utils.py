import sys, string, fcntl, os, random, regsub, re
import mm_cfg

# Valid toplevel domains for when we check the validity of an email address.

valid_toplevels = ["com", "edu", "gov", "int", "mil", "net", "org",
"inc", "af", "al", "dz", "as", "ad", "ao", "ai", "aq", "ag", "ar",
"am", "aw", "au", "at", "az", "bs", "bh", "bd", "bb", "by", "be",
"bz", "bj", "bm", "bt", "bo", "ba", "bw", "bv", "br", "io", "bn",
"bg", "bf", "bi", "kh", "cm", "ca", "cv", "ky", "cf", "td", "cl",
"cn", "cx", "cc", "co", "km", "cg", "ck", "cr", "ci", "hr", "cu",
"cy", "cz", "dk", "dj", "dm", "do", "tp", "ec", "eg", "sv", "gq",
"ee", "et", "fk", "fo", "fj", "fi", "fr", "gf", "pf", "tf", "ga",
"gm", "ge", "de", "gh", "gi", "gb", "uk", "gr", "gl", "gd", "gp",
"gu", "gt", "gn", "gw", "gy", "ht", "hm", "hn", "hk", "hu", "is",
"in", "id", "ir", "iq", "ie", "il", "it", "jm", "jp", "jo", "kz",
"ke", "ki", "kp", "kr", "kw", "kg", "la", "lv", "lb", "ls", "lr",
"ly", "li", "lt", "lu", "mo", "mg", "mw", "my", "mv", "ml", "mt",
"mh", "mq", "mr", "mu", "mx", "fm", "md", "mc", "mn", "ms", "ma",
"mz", "mm", "na", "nr", "np", "an", "nl", "nt", "nc", "nz", "ni",
"ne", "ng", "nu", "nf", "mp", "no", "om", "pk", "pw", "pa", "pg",
"py", "pe", "ph", "pn", "pl", "pt", "pr", "qa", "re", "ro", "ru",
"rw", "kn", "lc", "vc", "sm", "st", "sa", "sn", "sc", "sl", "sg",
"sk", "si", "sb", "so", "za", "es", "lk", "sh", "pm", "sd", "sr",
"sj", "sz", "se", "ch", "sy", "tw", "tj", "tz", "th", "tg", "tk",
"to", "tt", "tn", "tr", "tm", "tc", "tv", "ug", "ua", "um", "us",
"uy", "uz", "vu", "va", "ve", "vn", "vg", "vi", "wf", "eh", "ws",
"ye", "yu", "zr", "zm", "zw"]

def list_names():
    """Return the names of all lists in default list directory."""
    got = []
    for fn in os.listdir(mm_cfg.LIST_DATA_DIR):
	if not (
	    os.path.exists(
		os.path.join(os.path.join(mm_cfg.LIST_DATA_DIR, fn),
			     'config.db'))):
	    continue
	got.append(fn)
    return got

def SendTextToUser(subject, text, recipient, sender, errorsto=None):
    import mm_message
    msg = mm_message.OutgoingMessage()
    msg.SetSender(sender)
    msg.SetHeader('Subject', subject, 1)
    msg.SetBody(QuotePeriods(text))
    DeliverToUser(msg, recipient, errorsto=errorsto)

def DeliverToUser(msg, recipient, errorsto=None):
    """Use sendmail to deliver message."""

    # We fork to ensure no deadlock.  Otherwise, even if sendmail is
    # invoked in forking mode, if it eg detects a bad address before
    # forking, then it will try deliver to the errorsto addr *in the
    # foreground*.  If the errorsto happens to be the list owner for a list
    # that is doing the send - and holding a lock - then the delivery will
    # hang pending release of the lock - deadlock.
    if os.fork():
        return
    try:
        file = os.popen(mm_cfg.SENDMAIL_CMD % (msg.GetSender(), recipient),
                        'w')
        try:
            msg.headers.remove('\n')
        except ValueError:
            pass
        if not msg.getheader('to'):
            msg.headers.append('To: %s\n' % recipient)
        if errorsto:
            msg.headers.append('Errors-To: %s\n' % errorsto)
        file.write(string.join(msg.headers, '')+ '\n') 
        file.write(QuotePeriods(msg.body))
        file.close()
    finally:
        os._exit(0)

def QuotePeriods(text):
    return string.join(string.split(text, '\n.\n'), '\n .\n')

def ValidEmail(str):
    """Verify that the an email address isn't grossly invalid."""
    # Pretty minimal, cheesy check.  We could do better...
    if ((string.find(str, '|') <> -1) or (string.find(str, ';') <> -1)
	or str[0] == '-'):
	raise mm_err.MMHostileAddress
    if string.find(str, '/') <> -1:
	if os.path.isdir(os.path.split(str)[0]):
	    raise mm_err.MMHostileAddress
    user, domain_parts = ParseEmail(str)
    if not domain_parts:
	if string.find(str, '@') < 1:
	    return 0
	else:
	    return 1
    if len(domain_parts) < 2:
	return 0
    if domain_parts[-1] not in valid_toplevels:
	if len(domain_parts) <> 4:
	    return 0
	try:
	    domain_parts = map(eval, domain_parts) 
	except:
	    return 0
	for i in domain_parts:
	    if i < 0 or i > 255:
		return 0
    return 1


#
def GetPathPieces(path):
    l = string.split(path, '/')
    try:
	while 1:
	    l.remove('')
    except ValueError:
	pass
    return l

def MakeDirTree(path, perms=0775, verbose=0):
    made_part = '/'
    path_parts = GetPathPieces(path)
    for item in path_parts:
	made_part = os.path.join(made_part, item)
	if os.path.exists(made_part):
	    if not os.path.isdir(made_part):
		raise "RuntimeError", ("Couldn't make dir tree for %s.  (%s"
				       " already exists)" % (path, made_part))
	else:
	    ou = os.umask(0)
	    try:
		os.mkdir(made_part, perms)
	    finally:
		os.umask(ou)
	    if verbose:
		print 'made directory: ', madepart
  
# This takes an email address, and returns a tuple containing (user,host)
def ParseEmail(email):
    user = None
    domain = None
    email = string.lower(email)
    at_sign = string.find(email, '@')
    if at_sign < 1:
	return (email, None)
    user = email[:at_sign]
    rest = email[at_sign+1:]
    domain = string.split(rest, '.')
    return (user, domain)

# Return 1 if the 2 addresses match.  0 otherwise.
# Might also want to match if there's any common domain name...
# There's password protection anyway.

def AddressesMatch(addr1, addr2):
    "True when username matches and host addr of one addr contains other's."
    user1, domain1 = ParseEmail(addr1)
    user2, domain2 = ParseEmail(addr2)
    if user1 != user2:
	return 0
    if domain1 == domain2:
        return 1
    for i in range(-1 * min(len(domain1), len(domain2)), 0):
        # By going from most specific component of host part we're likely
        # to hit a difference sooner.
        if domain1[i] != domain2[i]:
            return 0
    return 1


def FindMatchingAddresses(name, array):
    """Given an email address, and a list of email addresses, returns the
    subset of the list that matches the given address.  Should sort based
    on exactness of match, just in case."""

    def CallAddressesMatch (x, y=name):
	return AddressesMatch(x,y)

    matches = filter(CallAddressesMatch, array)
    return matches
  
def GetRandomSeed():
    chr1 = int(random.random() * 57) + 65
    chr2 = int(random.random() * 57) + 65
    return "%c%c" % (chr1, chr2)


def SnarfMessage(msg):
    if msg.unixfrom:
	text = msg.unixfrom + string.join(msg.headers, '') + '\n' + msg.body
    else:
	text = string.join(msg.headers, '') + '\r\n' + msg.body
    return (msg.GetSender(), text) 


def QuoteHyperChars(str):
    arr = regsub.splitx(str, '[<>"&]')
    i = 1
    while i < len(arr):
	if arr[i] == '<':
	    arr[i] = '&lt;'
	elif arr[i] == '>':
	    arr[i] = '&gt;'
	elif arr[i] == '"':
	    arr[i] = '&quot;'
	else:     #if arr[i] == '&':
	    arr[i] = '&amp;'
	i = i + 2
    return string.join(arr, '')

# Just changing these two functions should be enough to control the way
# that email address obscuring is handled.

def ObscureEmail(addr, for_text=0):
    """Make email address unrecognizable to web spiders, but invertable.

    When for_text option is set (not default), make a sentence fragment
    instead of a token."""
    if for_text:
	return re.sub("@", " at ", addr)
    else:
	return re.sub("@", "__at__", addr)

def UnobscureEmail(addr):
    """Invert ObscureEmail() conversion."""
    # Contrived to act as an identity operation on already-unobscured
    # emails, so routines expecting obscured ones will accept both.
    return re.sub("__at__", "@", addr)

def map_maillists(func, names=None, unlock=None, verbose=0):
    """Apply function (of one argument) to all list objs in turn.

    Returns a list of the results.

    Optional arg 'names' specifies which lists, default all.
    Optional arg unlock says to unlock immediately after instantiation.
    Optional arg verbose says to print list name as it's about to be
    instantiated, CR when instantiation is complete, and result of
    application as it shows."""
    from maillist import MailList
    if names == None: names = list_names()
    got = []
    for i in names:
	if verbose: print i,
	l = MailList(i)
	if verbose: print
	if unlock and l.Locked():
	    l.Unlock()
	got.append(apply(func, (l,)))
	if verbose: print got[-1]
	if not unlock:
	    l.Unlock()
	del l
    return got

class Logger:
    def __init__(self, category):
	self.__category=category
	self.__f = None
    def __get_f(self):
	if self.__f:
	    return self.__f
	else:
	    fname = os.path.join(mm_cfg.LOG_DIR, self.__category)
	    try:
		ou = os.umask(002)
		try:
		    f = self.__f = open(fname, 'a+')
		finally:
		    os.umask(ou)
	    except IOError, msg:
		f = self.__f = sys.stderr
		f.write("logger open %s failed %s, using stderr\n"
			% (fname, msg))
	    return f
    def flush(self):
	f = self.__get_f()
	if hasattr(f, 'flush'):
	    f.flush()
    def write(self, msg):
	f = self.__get_f()
	try:
	    f.write(msg)
	except IOError, msg:
	    f = self.__f = sys.stderr
	    f.write("logger write %s failed %s, using stderr\n"
		    % (fname, msg))
    def writelines(self, lines):
	for l in lines:
	    self.write(l)
    def close(self):
	if not self.__f:
	    return
	self.__get_f().close()
    def __del__(self):
	try:
	    if self.__f and self.__f != sys.stderr:
		self.close()
	except:
	    pass
	    
class StampedLogger(Logger):
    """Record messages in log files, including date stamp and optional label.

    If manual_reset is off (default on), then timestamp will only be
    included in first .write() and in any writes that are preceeded by a
    call to the .reprime() method.  This is useful for when StampedLogger
    is substituting for sys.stderr, where you'd like to see the grouping of
    multiple writes under a single timestamp (and there is often is one 
    group, for uncaught exceptions where a script is bombing)."""

    def __init__(self, category, label=None, manual_reprime=0):
	"If specified, optional label is included after timestamp."
	self.label = label
        self.manual_reprime = manual_reprime
        self.primed = 1
	Logger.__init__(self, category)
    def reprime(self):
        """Reset so timestamp will be included with next write."""
        self.primed = 1
    def write(self, msg):
	import time
        if not self.manual_reprime or self.primed:
            stamp = time.strftime("%b %d %H:%M:%S %Y ",
                                  time.localtime(time.time()))
            self.primed = 0
        else:
            stamp = ""
	if self.label == None:
	    label = ""
	else:
	    label = "%s:" % self.label
	Logger.write(self, "%s%s %s" % (stamp, label, msg))
    def writelines(self, lines):
	first = 1
	for l in lines:
	    if first:
		self.write(l)
		first = 0
	    else:
		if l and l[0] not in [' ', '\t', '\n']:
		    Logger.write(self, ' ' + l)
		else:
		    Logger.write(self, l)
