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


"""Miscellaneous essential routines.

This includes actual message transmission routines, address checking and
message and address munging, a handy-dandy routine to map a function on all
the mailing lists, and whatever else doesn't belong elsewhere.

"""

import sys
import os
import string
import re
from UserDict import UserDict
from types import StringType
# XXX: obsolete, should use re module
import regsub
import random
import mm_cfg
import Errors
##try:
##    import md5
##except ImportError:
##    md5 = None



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


# a much more naive implementation than say, Emacs's fill-paragraph!
def wrap(text, column=70):
    """Wrap and fill the text to the specified column.

    Wrapping is always in effect, although if it is not possible to wrap a
    line (because some word is longer than `column' characters) the line is
    broken at the next available whitespace boundary.  Paragraphs are also
    always filled, unless the line begins with whitespace.  This is the
    algorithm that the Python FAQ wizard uses, and seems like a good
    compromise.

    """
    wrapped = ''
    # first split the text into paragraphs, defined as a blank line
    paras = re.split('\n\n', text)
    for para in paras:
        # fill
        lines = []
        fillprev = 0
        for line in string.split(para, '\n'):
            if not line:
                lines.append(line)
                continue
            if line[0] in string.whitespace:
                fillthis = 0
            else:
                fillthis = 1
            if fillprev and fillthis:
                # if the previous line should be filled, then just append a
                # single space, and the rest of the current line
                lines[-1] = string.rstrip(lines[-1]) + ' ' + line
            else:
                # no fill, i.e. retain newline
                lines.append(line)
            fillprev = fillthis
        # wrap each line
        for text in lines:
            while text:
                if len(text) <= column:
                    line = text
                    text = ''
                else:
                    bol = column
                    # find the last whitespace character
                    while bol > 0 and text[bol] not in string.whitespace:
                        bol = bol - 1
                    # now find the last non-whitespace character
                    eol = bol
                    while eol > 0 and text[eol] in string.whitespace:
                        eol = eol - 1
                    # watch out for text that's longer than the column width
                    if eol == 0:
                        # break on whitespace after column
                        eol = column
                        while eol < len(text) and \
                              text[eol] not in string.whitespace:
                            eol = eol + 1
                        bol = eol
                        while bol < len(text) and \
                              text[bol] in string.whitespace:
                            bol = bol + 1
                        bol = bol - 1
                    line = text[:eol+1] + '\n'
                    # find the next non-whitespace character
                    bol = bol + 1
                    while bol < len(text) and text[bol] in string.whitespace:
                        bol = bol + 1
                    text = text[bol:]
                wrapped = wrapped + line
            wrapped = wrapped + '\n'
            # end while text
        wrapped = wrapped + '\n'
        # end for text in lines
    # the last two newlines are bogus
    return wrapped[:-2]
    


def QuotePeriods(text):
    return string.join(string.split(text, '\n.\n'), '\n .\n')


# TBD: what other characters should be disallowed?
_badchars = re.compile('[][()<>|;^,]')

def ValidateEmail(str):
    """Verify that the an email address isn't grossly invalid."""
    # Pretty minimal, cheesy check.  We could do better...
    if not str:
        raise Errors.MMBadEmailError
    if _badchars.search(str) or str[0] == '-':
        raise Errors.MMHostileAddress
    if string.find(str, '/') <> -1 and \
       os.path.isdir(os.path.split(str)[0]):
        # then
        raise Errors.MMHostileAddress
    user, domain_parts = ParseEmail(str)
    # this means local, unqualified addresses, are no allowed
    if not domain_parts:
        raise Errors.MMBadEmailError
    if len(domain_parts) < 2:
	raise Errors.MMBadEmailError



# User J. Person <person@allusers.com>
_addrcre1 = re.compile('<(.*)>')
# person@allusers.com (User J. Person)
_addrcre2 = re.compile('([^(]*)\s(.*)')

def ParseAddrs(addresses):
    """Parse common types of email addresses:

    User J. Person <person@allusers.com>
    person@allusers.com (User J. Person)

    TBD: I wish we could use rfc822.parseaddr() but 1) the interface is not
    convenient, and 2) it doesn't work for the second type of address.

    Argument is a list of addresses, return value is a list of the parsed
    email addresses.  The argument can also be a single string, in which case
    the return value is a single string.  All addresses are string.strip()'d.

    """
    single = 0
    if type(addresses) == type(''):
        single = 1
        addrs = [addresses]
    else:
        addrs = addresses
    parsed = []
    for a in addrs:
        mo = _addrcre1.search(a)
        if mo:
            parsed.append(mo.group(1))
            continue
        mo = _addrcre2.search(a)
        if mo:
            parsed.append(mo.group(1))
            continue
        parsed.append(a)
    if single:
        return string.strip(parsed[0])
    return map(string.strip, parsed)



def GetPathPieces(path):
    l = string.split(path, '/')
    try:
	while 1:
	    l.remove('')
    except ValueError:
	pass
    return l


_nesting_level = None
def GetNestingLevel():
    global _nesting_level
    if _nesting_level == None:
        try:
            path = os.environ['PATH_INFO']
            if path[0] <> '/': 
                path= '/' + path
            _nesting_level = len(string.split(path, '/')) - 1
        except KeyError:
            _nesting_level = 0
    return _nesting_level



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


def LCDomain(addr):
    "returns the address with the domain part lowercased"
    atind = string.find(addr, '@')
    if atind == -1: # no domain part
        return addr
    return addr[:atind] + '@' + string.lower(addr[atind + 1:])



# Return 1 if the 2 addresses match.  0 otherwise.
# Might also want to match if there's any common domain name...
# There's password protection anyway.
def AddressesMatch(addr1, addr2):
    "True when username matches and host addr of one addr contains other's."
    addr1, addr2 = map(LCDomain, [addr1, addr2])
    if not mm_cfg.SMART_ADDRESS_MATCH:
        return addr1 == addr2
    user1, domain1 = ParseEmail(addr1)
    user2, domain2 = ParseEmail(addr2)
    if user1 != user2:
	return 0
    if domain1 == domain2:
        return 1
    elif not domain1 or not domain2:
        return 0
    for i in range(-1 * min(len(domain1), len(domain2)), 0):
        # By going from most specific component of host part we're likely
        # to hit a difference sooner.
        if domain1[i] != domain2[i]:
            return 0
    return 1



def GetPossibleMatchingAddrs(name):
    """returns a sorted list of addresses that could possibly match
    a given name.

    For Example, given scott@pobox.com, return ['scott@pobox.com'],
    given scott@blackbox.pobox.com return ['scott@blackbox.pobox.com',
                                           'scott@pobox.com']"""

    name = string.lower(name)
    user, domain = ParseEmail(name)
    res = [name]
    if domain:
        domain = domain[1:]
        while len(domain) >= 2:
            res.append("%s@%s" % (user, string.join(domain, ".")))
            domain = domain[1:]
    return res



def List2Dict(list):
    """List2Dict returns a dict keyed by the entries in the list
    passed to it."""
    res = {}
    for item in list:
        res[item] = 1
    return res


def FindMatchingAddresses(name, dict, *dicts):
    """Given an email address, and any number of dictionaries keyed by
    email addresses, returns the subset of the list that matches the
    given address.  Should sort based on exactness of match,
    just in case."""
    dicts = list(dicts)
    dicts.insert(0, dict)
    if not mm_cfg.SMART_ADDRESS_MATCH:
        for d in dicts:
            if d.has_key(string.lower(name)):
                return [name]
        return []
    #
    # GetPossibleMatchingAddrs return string.lower'd values
    #
    p_matches = GetPossibleMatchingAddrs(name) 
    res = []
    for pm in p_matches:
        for d in dicts:
            if d.has_key(pm):
                res.append(pm)
    return res

  

def GetRandomSeed():
    chr1 = int(random.random() * 52)
    chr2 = int(random.random() * 52)
    def mkletter(c):
        if 0 <= c < 26:
            c = c + 65
        if 26 <= c < 52:
            c = c - 26 + 97
        return c
    return "%c%c" % tuple(map(mkletter, (chr1, chr2)))


def MakeRandomPassword(length=4):
    password = ""
    while len(password) < length:
        password = password + GetRandomSeed()
    password = password[:length]
    return password



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
	return string.replace(addr, "@", " at ")
    else:
	return string.replace(addr, "@", "--at--")

def UnobscureEmail(addr):
    """Invert ObscureEmail() conversion."""
    # Contrived to act as an identity operation on already-unobscured
    # emails, so routines expecting obscured ones will accept both.
    return string.replace(addr, "--at--", "@")



def map_maillists(func, names=None, unlock=None, verbose=0):
    """Apply function (of one argument) to all list objs in turn.

    Returns a list of the results.

    Optional arg 'names' specifies which lists, default all.
    Optional arg unlock says to unlock immediately after instantiation.
    Optional arg verbose says to print list name as it's about to be
    instantiated, CR when instantiation is complete, and result of
    application as it shows."""
    from MailList import MailList
    if names == None:
        names = list_names()
    got = []
    for i in names:
	if verbose:
            print i,
	l = MailList(i)
	if verbose:
            print
	if unlock and l.Locked():
	    l.Unlock()
	got.append(apply(func, (l,)))
	if verbose:
            print got[-1]
	if not unlock:
	    l.Unlock()
	del l
    return got



def chunkify(members, chunksize=None):
     """
     return a list of lists of members
     """
     if chunksize is None:
         chunksize = mm_cfg.DEFAULT_ADMIN_MEMBER_CHUNKSIZE
     members.sort()
     res = []
     while 1:
         if not members:
             break
         chunk = members[:chunksize]
         res.append(chunk)
         members = members[chunksize:]
     return res



class SafeDict(UserDict):
    """Dictionary which returns a default value for unknown keys.

    This is used in maketext so that editing templates is a bit more robust.
    """
    def __init__(self, d=None):
        # optional initial dictionary is a Python 1.5.2-ism.  Do it this way
        # for portability
        UserDict.__init__(self)
        if d is not None:
            self.update(d)

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            if type(key) == StringType:
                return '%('+key+')s'
            else:
                return '<Missing key: %s>' % `key`


def maketext(templatefile, dict, raw=0):
    """Make some text from a template file.

    Reads the `templatefile', relative to mm_cfg.TEMPLATE_DIR, does string
    substitution by interpolating in the `dict', and if `raw' is false,
    wraps/fills the resulting text by calling wrap().
    """
    file = os.path.join(mm_cfg.TEMPLATE_DIR, templatefile)
    fp = open(file)
    template = fp.read()
    fp.close()
    text = template % SafeDict(dict)
    if raw:
        return text
    return wrap(text)



# given a Message.Message object, test for administrivia (eg subscribe,
# unsubscribe, etc).  the test must be a good guess -- messages that return
# true get sent to the list admin instead of the entire list.
#
def IsAdministrivia(msg):
    lines = map(string.lower, string.split(msg.body, "\n"))
    # check to see how many lines that actually have text in them there are
    admin_data = {"subscribe": (0, 3),
                  "unsubscribe": (0, 1),
                  "who": (0,0),
                  "info": (0,0),
                  "lists": (0,0),
                  "set": (3, 3),
                  "help": (0,0),
                  "password": (2, 2),
                  "options": (0,0),
                  "remove": (0, 0)}
    lines_with_text = 0
    for line in lines:
        if string.strip(line):
            lines_with_text = lines_with_text + 1
        if lines_with_text > mm_cfg.DEFAULT_MAIL_COMMANDS_MAX_LINES:
            return 0
    sig_ind =  string.find(msg.body, "\n-- ")
    if sig_ind != -1:
        body = msg.body[:sig_ind]
    else:
        body = msg.body
    if admin_data.has_key(string.lower(string.strip(body))):
        return 1
    try:
        if admin_data.has_key(string.lower(string.strip(msg["subject"]))):
            return 1
    except KeyError:
        pass
    for line in lines[:5]:
        if not string.strip(line):
            continue
        words = string.split(line)
        if admin_data.has_key(words[0]):
            min_args, max_args = admin_data[words[0]]
            if min_args <= len(words[1:]) <= max_args:
                if (words[0] == 'set'
                    and (words[2] not in ['on', 'off'])):
                    continue
                return 1
    return 0

        

def reraise(exc=None, val=None):
    """Use this function to re-raise an exception.

    This implementation hides the differences between Python versions.
    Optional exc is the exception type to raise.  When exc is not None,
    optional val is the exception value to raise.

    """
    # Python 1.5.2
    # raise
    # Earlier Python versions
    if exc is None:
        t, v, tb = sys.exc_info()
        raise t, v, tb
    raise exc, val, sys.exc_info()[2]



def mkdir(dir, mode=02775):
    """Wraps os.mkdir() in a umask saving try/finally.
Two differences from os.mkdir():
    - umask is forced to 0 during mkdir()
    - default mode is 02775
"""
    ou = os.umask(0)
    try:
        os.mkdir(dir, mode)
    finally:
        os.umask(ou)



def open_ex(filename, mode='r', bufsize=-1, perms=0664):
    """Use os.open() to open a file in a particular mode.

    Returns a file-like object instead of a file descriptor.
    Also umask is forced to 0 during the open().

    `b' flag is currently unsupported."""
    modekey = mode
    trunc = os.O_TRUNC
    if mode == 'r':
        trunc = 0
    elif mode[-1] == '+':
        trunc = 0
        modekey = mode[:-1]
    else:
        trunc = os.O_TRUNC
    flags = {'r' : os.O_RDONLY,
             'w' : os.O_WRONLY | os.O_CREAT,
             'a' : os.O_RDWR   | os.O_CREAT | os.O_APPEND,
             'rw': os.O_RDWR   | os.O_CREAT,
             # TBD: should also support `b'
             }.get(modekey)
    if flags is None:
        raise TypeError, 'Unsupported file mode: ' + mode
    flags = flags | trunc
    ou = os.umask(0)
    try:
        try:
            fd = os.open(filename, flags, perms)
            fp = os.fdopen(fd, mode, bufsize)
            return fp
        # transform any os.errors into IOErrors
        except os.error, e:
            reraise(IOError, e)
    finally:
        os.umask(ou)



def GetRequestURI(fallback=None):
    """Return the full virtual path this CGI script was invoked with.

    Newer web servers seems to supply this info in the REQUEST_URI
    environment variable -- which isn't part of the CGI/1.1 spec.
    Thus, if REQUEST_URI isn't available, we concatenate SCRIPT_NAME
    and PATH_INFO, both of which are part of CGI/1.1.

    Optional argument `fallback' (default `None') is returned if both of
    the above methods fail.

    """
    if os.environ.has_key('REQUEST_URI'):
        return os.environ['REQUEST_URI']
    elif os.environ.has_key('SCRIPT_NAME') and os.environ.has_key('PATH_INFO'):
        return os.environ['SCRIPT_NAME'] + os.environ['PATH_INFO']
    else:
        return fallback
