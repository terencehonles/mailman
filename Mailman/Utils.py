import string, fcntl, os, random, regsub
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

# Make sure the email address passed isn't grossly invalid.
# Pretty minimal, cheesy check.  We could do better...
def ValidEmail(str):
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

def MakeDirTree(path, perms=0774, verbose=0):
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
    user1, domain1 = ParseEmail(addr1)
    user2, domain2 = ParseEmail(addr2)
    if user1 <> user2:
	return 0
    if domain1 == domain2:
	return 1
    l = max(len(domain1), len(domain2)) - 1
    if l < 2:
	return 0
    for i in range(l):
	if domain1[-(i+1)] <> domain2[-(i+1)]:
	    return 0
	return 1
    return 0

# Given an email address, and a list of email addresses,
# returns the subset of the list that matches the given address.
# Should sort based on exactness of match, just in case.
def FindMatchingAddresses(name, array):

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
