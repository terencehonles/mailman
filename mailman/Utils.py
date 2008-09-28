# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Miscellaneous essential routines.

This includes actual message transmission routines, address checking and
message and address munging, a handy-dandy routine to map a function on all
the mailing lists, and whatever else doesn't belong elsewhere.
"""

import os
import re
import cgi
import sha
import time
import errno
import base64
import random
import logging
import urlparse
import htmlentitydefs
import email.Header
import email.Iterators

from email.Errors import HeaderParseError
from string import ascii_letters, digits, whitespace, Template

import mailman.templates

from mailman import passwords
from mailman.configuration import config
from mailman.core import errors

AT = '@'
CR = '\r'
DOT = '.'
EMPTYSTRING = ''
IDENTCHARS = ascii_letters + digits + '_'
NL = '\n'
UEMPTYSTRING = u''
TEMPLATE_DIR = os.path.dirname(mailman.templates.__file__)

# Search for $(identifier)s strings, except that the trailing s is optional,
# since that's a common mistake
cre = re.compile(r'%\(([_a-z]\w*?)\)s?', re.IGNORECASE)
# Search for $$, $identifier, or ${identifier}
dre = re.compile(r'(\${2})|\$([_a-z]\w*)|\${([_a-z]\w*)}', re.IGNORECASE)

log = logging.getLogger('mailman.error')



def list_exists(fqdn_listname):
    """Return true iff list `fqdn_listname' exists."""
    return config.db.list_manager.get(fqdn_listname) is not None


def list_names():
    """Return the fqdn names of all lists in default list directory."""
    return ['%s@%s' % (listname, hostname)
            for listname, hostname in config.db.list_manager.get_list_names()]


def split_listname(listname):
    if AT in listname:
        return listname.split(AT, 1)
    return listname, config.DEFAULT_EMAIL_HOST


def fqdn_listname(listname, hostname=None):
    if hostname is None:
        return AT.join(split_listname(listname))
    return AT.join((listname, hostname))



# a much more naive implementation than say, Emacs's fill-paragraph!
def wrap(text, column=70, honor_leading_ws=True):
    """Wrap and fill the text to the specified column.

    Wrapping is always in effect, although if it is not possible to wrap a
    line (because some word is longer than `column' characters) the line is
    broken at the next available whitespace boundary.  Paragraphs are also
    always filled, unless honor_leading_ws is true and the line begins with
    whitespace.  This is the algorithm that the Python FAQ wizard uses, and
    seems like a good compromise.

    """
    wrapped = ''
    # first split the text into paragraphs, defined as a blank line
    paras = re.split('\n\n', text)
    for para in paras:
        # fill
        lines = []
        fillprev = False
        for line in para.split(NL):
            if not line:
                lines.append(line)
                continue
            if honor_leading_ws and line[0] in whitespace:
                fillthis = False
            else:
                fillthis = True
            if fillprev and fillthis:
                # if the previous line should be filled, then just append a
                # single space, and the rest of the current line
                lines[-1] = lines[-1].rstrip() + ' ' + line
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
                    while bol > 0 and text[bol] not in whitespace:
                        bol -= 1
                    # now find the last non-whitespace character
                    eol = bol
                    while eol > 0 and text[eol] in whitespace:
                        eol -= 1
                    # watch out for text that's longer than the column width
                    if eol == 0:
                        # break on whitespace after column
                        eol = column
                        while eol < len(text) and text[eol] not in whitespace:
                            eol += 1
                        bol = eol
                        while bol < len(text) and text[bol] in whitespace:
                            bol += 1
                        bol -= 1
                    line = text[:eol+1] + '\n'
                    # find the next non-whitespace character
                    bol += 1
                    while bol < len(text) and text[bol] in whitespace:
                        bol += 1
                    text = text[bol:]
                wrapped += line
            wrapped += '\n'
            # end while text
        wrapped += '\n'
        # end for text in lines
    # the last two newlines are bogus
    return wrapped[:-2]



def QuotePeriods(text):
    JOINER = '\n .\n'
    SEP = '\n.\n'
    return JOINER.join(text.split(SEP))


# This takes an email address, and returns a tuple containing (user,host)
def ParseEmail(email):
    user = None
    domain = None
    email = email.lower()
    at_sign = email.find('@')
    if at_sign < 1:
        return email, None
    user = email[:at_sign]
    rest = email[at_sign+1:]
    domain = rest.split('.')
    return user, domain


def LCDomain(addr):
    "returns the address with the domain part lowercased"
    atind = addr.find('@')
    if atind == -1: # no domain part
        return addr
    return addr[:atind] + '@' + addr[atind+1:].lower()


# TBD: what other characters should be disallowed?
_badchars = re.compile(r'[][()<>|;^,\000-\037\177-\377]')

def ValidateEmail(s):
    """Verify that the an email address isn't grossly evil."""
    # Pretty minimal, cheesy check.  We could do better...
    if not s or ' ' in s:
        raise errors.InvalidEmailAddress(repr(s))
    if _badchars.search(s) or s[0] == '-':
        raise errors.InvalidEmailAddress(repr(s))
    user, domain_parts = ParseEmail(s)
    # Local, unqualified addresses are not allowed.
    if not domain_parts:
        raise errors.InvalidEmailAddress(repr(s))
    if len(domain_parts) < 2:
        raise errors.InvalidEmailAddress(repr(s))



# Patterns which may be used to form malicious path to inject a new
# line in the mailman error log. (TK: advisory by Moritz Naumann)
CRNLpat = re.compile(r'[^\x21-\x7e]')

def GetPathPieces(envar='PATH_INFO'):
    path = os.environ.get(envar)
    if path:
        if CRNLpat.search(path):
            path = CRNLpat.split(path)[0]
            log.error('Warning: Possible malformed path attack.')
        return [p for p in path.split('/') if p]
    return []



def ScriptURL(target):
    up = '../' * len(GetPathPieces())
    return '%s%s' % (up, target + config.CGIEXT)



def GetPossibleMatchingAddrs(name):
    """returns a sorted list of addresses that could possibly match
    a given name.

    For Example, given scott@pobox.com, return ['scott@pobox.com'],
    given scott@blackbox.pobox.com return ['scott@blackbox.pobox.com',
                                           'scott@pobox.com']"""

    name = name.lower()
    user, domain = ParseEmail(name)
    res = [name]
    if domain:
        domain = domain[1:]
        while len(domain) >= 2:
            res.append("%s@%s" % (user, DOT.join(domain)))
            domain = domain[1:]
    return res



def List2Dict(L, foldcase=False):
    """Return a dict keyed by the entries in the list passed to it."""
    d = {}
    if foldcase:
        for i in L:
            d[i.lower()] = True
    else:
        for i in L:
            d[i] = True
    return d



_vowels = ('a', 'e', 'i', 'o', 'u')
_consonants = ('b', 'c', 'd', 'f', 'g', 'h', 'k', 'm', 'n',
               'p', 'r', 's', 't', 'v', 'w', 'x', 'z')
_syllables = []

for v in _vowels:
    for c in _consonants:
        _syllables.append(c+v)
        _syllables.append(v+c)
del c, v

def UserFriendly_MakeRandomPassword(length):
    syls = []
    while len(syls) * 2 < length:
        syls.append(random.choice(_syllables))
    return EMPTYSTRING.join(syls)[:length]


def Secure_MakeRandomPassword(length):
    bytesread = 0
    bytes = []
    fd = None
    try:
        while bytesread < length:
            try:
                # Python 2.4 has this on available systems.
                newbytes = os.urandom(length - bytesread)
            except (AttributeError, NotImplementedError):
                if fd is None:
                    try:
                        fd = os.open('/dev/urandom', os.O_RDONLY)
                    except OSError, e:
                        if e.errno <> errno.ENOENT:
                            raise
                        # We have no available source of cryptographically
                        # secure random characters.  Log an error and fallback
                        # to the user friendly passwords.
                        log.error('urandom not available, passwords not secure')
                        return UserFriendly_MakeRandomPassword(length)
                newbytes = os.read(fd, length - bytesread)
            bytes.append(newbytes)
            bytesread += len(newbytes)
        s = base64.encodestring(EMPTYSTRING.join(bytes))
        # base64 will expand the string by 4/3rds
        return s.replace('\n', '')[:length]
    finally:
        if fd is not None:
            os.close(fd)


def MakeRandomPassword(length=None):
    if length is None:
        length = config.MEMBER_PASSWORD_LENGTH
    if config.USER_FRIENDLY_PASSWORDS:
        password = UserFriendly_MakeRandomPassword(length)
    else:
        password = Secure_MakeRandomPassword(length)
    return password.decode('ascii')


def GetRandomSeed():
    chr1 = int(random.random() * 52)
    chr2 = int(random.random() * 52)
    def mkletter(c):
        if 0 <= c < 26:
            c += 65
        if 26 <= c < 52:
            #c = c - 26 + 97
            c += 71
        return c
    return "%c%c" % tuple(map(mkletter, (chr1, chr2)))



def set_global_password(pw, siteadmin=True, scheme=None):
    if scheme is None:
        scheme = passwords.Schemes.ssha
    if siteadmin:
        filename = config.SITE_PW_FILE
    else:
        filename = config.LISTCREATOR_PW_FILE
    try:
        fp = open(filename, 'w')
        print >> fp, passwords.make_secret(pw, scheme)
    finally:
        fp.close()


def get_global_password(siteadmin=True):
    if siteadmin:
        filename = config.SITE_PW_FILE
    else:
        filename = config.LISTCREATOR_PW_FILE
    try:
        fp = open(filename)
        challenge = fp.read()[:-1]                # strip off trailing nl
        fp.close()
    except IOError, e:
        if e.errno <> errno.ENOENT:
            raise
        # It's okay not to have a site admin password
        return None
    return challenge


def check_global_password(response, siteadmin=True):
    challenge = get_global_password(siteadmin)
    if challenge is None:
        return False
    return passwords.check_response(challenge, response)



def websafe(s):
    return cgi.escape(s, quote=True)


def nntpsplit(s):
    parts = s.split(':', 1)
    if len(parts) == 2:
        try:
            return parts[0], int(parts[1])
        except ValueError:
            pass
    # Use the defaults
    return s, 119



# Just changing these two functions should be enough to control the way
# that email address obscuring is handled.
def ObscureEmail(addr, for_text=False):
    """Make email address unrecognizable to web spiders, but invertable.

    When for_text option is set (not default), make a sentence fragment
    instead of a token."""
    if for_text:
        return addr.replace('@', ' at ')
    else:
        return addr.replace('@', '--at--')

def UnobscureEmail(addr):
    """Invert ObscureEmail() conversion."""
    # Contrived to act as an identity operation on already-unobscured
    # emails, so routines expecting obscured ones will accept both.
    return addr.replace('--at--', '@')



class OuterExit(Exception):
    pass

def findtext(templatefile, dict=None, raw=False, lang=None, mlist=None):
    # Make some text from a template file.  The order of searches depends on
    # whether mlist and lang are provided.  Once the templatefile is found,
    # string substitution is performed by interpolation in `dict'.  If `raw'
    # is false, the resulting text is wrapped/filled by calling wrap().
    #
    # When looking for a template in a specific language, there are 4 places
    # that are searched, in this order:
    #
    # 1. the list-specific language directory
    #    lists/<listname>/<language>
    #
    # 2. the domain-specific language directory
    #    templates/<list.host_name>/<language>
    #
    # 3. the site-wide language directory
    #    templates/site/<language>
    #
    # 4. the global default language directory
    #    templates/<language>
    #
    # The first match found stops the search.  In this way, you can specialize
    # templates at the desired level, or, if you use only the default
    # templates, you don't need to change anything.  You should never modify
    # files in the templates/<language> subdirectory, since Mailman will
    # overwrite these when you upgrade.  That's what the templates/site
    # language directories are for.
    #
    # A further complication is that the language to search for is determined
    # by both the `lang' and `mlist' arguments.  The search order there is
    # that if lang is given, then the 4 locations above are searched,
    # substituting lang for <language>.  If no match is found, and mlist is
    # given, then the 4 locations are searched using the list's preferred
    # language.  After that, the server default language is used for
    # <language>.  If that still doesn't yield a template, then the standard
    # distribution's English language template is used as an ultimate
    # fallback, and when lang is not 'en', the resulting template is passed
    # through the translation service.  If this template is missing you've got
    # big problems. ;)
    #
    # A word on backwards compatibility: Mailman versions prior to 2.1 stored
    # templates in templates/*.{html,txt} and lists/<listname>/*.{html,txt}.
    # Those directories are no longer searched so if you've got customizations
    # in those files, you should move them to the appropriate directory based
    # on the above description.  Mailman's upgrade script cannot do this for
    # you.
    #
    # The function has been revised and renamed as it now returns both the
    # template text and the path from which it retrieved the template. The
    # original function is now a wrapper which just returns the template text
    # as before, by calling this renamed function and discarding the second
    # item returned.
    #
    # Calculate the languages to scan
    languages = set()
    if lang is not None:
        languages.add(lang)
    if mlist is not None:
        languages.add(mlist.preferred_language)
    languages.add(config.DEFAULT_SERVER_LANGUAGE)
    assert None not in languages, 'None in languages'
    # Calculate the locations to scan
    searchdirs = []
    if mlist is not None:
        searchdirs.append(mlist.data_path)
        searchdirs.append(os.path.join(TEMPLATE_DIR, mlist.host_name))
    searchdirs.append(os.path.join(TEMPLATE_DIR, 'site'))
    searchdirs.append(TEMPLATE_DIR)
    # Start scanning
    fp = None
    try:
        for lang in languages:
            for dir in searchdirs:
                filename = os.path.join(dir, lang, templatefile)
                try:
                    fp = open(filename)
                    raise OuterExit
                except IOError, e:
                    if e.errno <> errno.ENOENT: raise
                    # Okay, it doesn't exist, keep looping
                    fp = None
    except OuterExit:
        pass
    if fp is None:
        # Try one last time with the distro English template, which, unless
        # you've got a really broken installation, must be there.
        try:
            filename = os.path.join(TEMPLATE_DIR, 'en', templatefile)
            fp = open(filename)
        except IOError, e:
            if e.errno <> errno.ENOENT:
                raise
            # We never found the template.  BAD!
            raise IOError(errno.ENOENT, 'No template file found', templatefile)
        else:
            from mailman.i18n import get_translation
            # XXX BROKEN HACK
            data = fp.read()[:-1]
            template = get_translation().ugettext(data)
            fp.close()
    else:
        template = fp.read()
        fp.close()
        template = unicode(template, GetCharSet(lang), 'replace')
    text = template
    if dict is not None:
        try:
            text = Template(template).safe_substitute(**dict)
        except (TypeError, ValueError):
            # The template is really screwed up
            log.exception('broken template: %s', filename)
    if raw:
        return text, filename
    return wrap(text), filename


def maketext(templatefile, dict=None, raw=False, lang=None, mlist=None):
    return findtext(templatefile, dict, raw, lang, mlist)[0]



def GetRequestURI(fallback=None, escape=True):
    """Return the full virtual path this CGI script was invoked with.

    Newer web servers seems to supply this info in the REQUEST_URI
    environment variable -- which isn't part of the CGI/1.1 spec.
    Thus, if REQUEST_URI isn't available, we concatenate SCRIPT_NAME
    and PATH_INFO, both of which are part of CGI/1.1.

    Optional argument `fallback' (default `None') is returned if both of
    the above methods fail.

    The url will be cgi escaped to prevent cross-site scripting attacks,
    unless `escape' is set to 0.
    """
    url = fallback
    if 'REQUEST_URI' in os.environ:
        url = os.environ['REQUEST_URI']
    elif 'SCRIPT_NAME' in os.environ and 'PATH_INFO' in os.environ:
        url = os.environ['SCRIPT_NAME'] + os.environ['PATH_INFO']
    if escape:
        return websafe(url)
    return url



# Wait on a dictionary of child pids
def reap(kids, func=None, once=False):
    while kids:
        if func:
            func()
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except OSError, e:
            # If the child procs had a bug we might have no children
            if e.errno <> errno.ECHILD:
                raise
            kids.clear()
            break
        if pid <> 0:
            try:
                del kids[pid]
            except KeyError:
                # Huh?  How can this happen?
                pass
        if once:
            break



def makedirs(path, mode=02775):
    try:
        omask = os.umask(0)
        try:
            os.makedirs(path, mode)
        finally:
            os.umask(omask)
    except OSError, e:
        # Ignore the exceptions if the directory already exists
        if e.errno <> errno.EEXIST:
            raise



# XXX Replace this with direct calls.  For now, existing uses of GetCharSet()
# are too numerous to change.
def GetCharSet(lang):
    return config.languages.get_charset(lang)



def get_request_domain():
    host = os.environ.get('HTTP_HOST', os.environ.get('SERVER_NAME'))
    port = os.environ.get('SERVER_PORT')
    # Strip off the port if there is one
    if port and host.endswith(':' + port):
        host = host[:-len(port)-1]
    return host.lower()


def get_site_noreply():
    return '%s@%s' % (config.NO_REPLY_ADDRESS, config.DEFAULT_EMAIL_HOST)



# Figure out epoch seconds of midnight at the start of today (or the given
# 3-tuple date of (year, month, day).
def midnight(date=None):
    if date is None:
        date = time.localtime()[:3]
    # -1 for dst flag tells the library to figure it out
    return time.mktime(date + (0,)*5 + (-1,))



# Utilities to convert from simplified $identifier substitutions to/from
# standard Python $(identifier)s substititions.  The "Guido rules" for the
# former are:
#    $$ -> $
#    $identifier -> $(identifier)s
#    ${identifier} -> $(identifier)s

def to_dollar(s):
    """Convert from %-strings to $-strings."""
    s = s.replace('$', '$$').replace('%%', '%')
    parts = cre.split(s)
    for i in range(1, len(parts), 2):
        if parts[i+1] and parts[i+1][0] in IDENTCHARS:
            parts[i] = '${' + parts[i] + '}'
        else:
            parts[i] = '$' + parts[i]
    return EMPTYSTRING.join(parts)


def to_percent(s):
    """Convert from $-strings to %-strings."""
    s = s.replace('%', '%%').replace('$$', '$')
    parts = dre.split(s)
    for i in range(1, len(parts), 4):
        if parts[i] is not None:
            parts[i] = '$'
        elif parts[i+1] is not None:
            parts[i+1] = '%(' + parts[i+1] + ')s'
        else:
            parts[i+2] = '%(' + parts[i+2] + ')s'
    return EMPTYSTRING.join(filter(None, parts))


def dollar_identifiers(s):
    """Return the set (dictionary) of identifiers found in a $-string."""
    d = {}
    for name in filter(None, [b or c or None for a, b, c in dre.findall(s)]):
        d[name] = True
    return d


def percent_identifiers(s):
    """Return the set (dictionary) of identifiers found in a %-string."""
    d = {}
    for name in cre.findall(s):
        d[name] = True
    return d



# Utilities to canonicalize a string, which means un-HTML-ifying the string to
# produce a Unicode string or an 8-bit string if all the characters are ASCII.
def canonstr(s, lang=None):
    newparts = []
    parts = re.split(r'&(?P<ref>[^;]+);', s)
    def appchr(i):
        if i < 256:
            newparts.append(chr(i))
        else:
            newparts.append(unichr(i))
    while True:
        newparts.append(parts.pop(0))
        if not parts:
            break
        ref = parts.pop(0)
        if ref.startswith('#'):
            try:
                appchr(int(ref[1:]))
            except ValueError:
                # Non-convertable, stick with what we got
                newparts.append('&'+ref+';')
        else:
            c = htmlentitydefs.entitydefs.get(ref, '?')
            if c.startswith('#') and c.endswith(';'):
                appchr(int(ref[1:-1]))
            else:
                newparts.append(c)
    newstr = EMPTYSTRING.join(newparts)
    if isinstance(newstr, unicode):
        return newstr
    # We want the default fallback to be iso-8859-1 even if the language is
    # English (us-ascii).  This seems like a practical compromise so that
    # non-ASCII characters in names can be used in English lists w/o having to
    # change the global charset for English from us-ascii (which I
    # superstitiously think may have unintended consequences).
    if lang is None:
        charset = 'iso-8859-1'
    else:
        charset = GetCharSet(lang)
        if charset == 'us-ascii':
            charset = 'iso-8859-1'
    return unicode(newstr, charset, 'replace')


# The opposite of canonstr() -- sorta.  I.e. it attempts to encode s in the
# charset of the given language, which is the character set that the page will
# be rendered in, and failing that, replaces non-ASCII characters with their
# html references.  It always returns a byte string.
def uncanonstr(s, lang=None):
    if s is None:
        s = u''
    if lang is None:
        charset = 'us-ascii'
    else:
        charset = GetCharSet(lang)
    # See if the string contains characters only in the desired character
    # set.  If so, return it unchanged, except for coercing it to a byte
    # string.
    try:
        if isinstance(s, unicode):
            return s.encode(charset)
        else:
            u = unicode(s, charset)
            return s
    except UnicodeError:
        # Nope, it contains funny characters, so html-ref it
        return uquote(s)


def uquote(s):
    a = []
    for c in s:
        o = ord(c)
        if o > 127:
            a.append('&#%3d;' % o)
        else:
            a.append(c)
    # Join characters together and coerce to byte string
    return str(EMPTYSTRING.join(a))


def oneline(s, cset='us-ascii', in_unicode=False):
    # Decode header string in one line and convert into specified charset
    try:
        h = email.Header.make_header(email.Header.decode_header(s))
        ustr = h.__unicode__()
        line = UEMPTYSTRING.join(ustr.splitlines())
        if in_unicode:
            return line
        else:
            return line.encode(cset, 'replace')
    except (LookupError, UnicodeError, ValueError, HeaderParseError):
        # possibly charset problem. return with undecoded string in one line.
        return EMPTYSTRING.join(s.splitlines())


def strip_verbose_pattern(pattern):
    # Remove white space and comments from a verbose pattern and return a
    # non-verbose, equivalent pattern.  Replace CR and NL in the result
    # with '\\r' and '\\n' respectively to avoid multi-line results.
    if not isinstance(pattern, str):
        return pattern
    newpattern = ''
    i = 0
    inclass = False
    skiptoeol = False
    copynext = False
    while i < len(pattern):
        c = pattern[i]
        if copynext:
            if c == NL:
                newpattern += '\\n'
            elif c == CR:
                newpattern += '\\r'
            else:
                newpattern += c
            copynext = False
        elif skiptoeol:
            if c == NL:
                skiptoeol = False
        elif c == '#' and not inclass:
            skiptoeol = True
        elif c == '[' and not inclass:
            inclass = True
            newpattern += c
            copynext = True
        elif c == ']' and inclass:
            inclass = False
            newpattern += c
        elif re.search('\s', c):
            if inclass:
                if c == NL:
                    newpattern += '\\n'
                elif c == CR:
                    newpattern += '\\r'
                else:
                    newpattern += c
        elif c == '\\' and not inclass:
            newpattern += c
            copynext = True
        else:
            if c == NL:
                newpattern += '\\n'
            elif c == CR:
                newpattern += '\\r'
            else:
                newpattern += c
        i += 1
    return newpattern



def get_pattern(email, pattern_list):
    """Returns matched entry in pattern_list if email matches.
    Otherwise returns None.
    """
    if not pattern_list:
        return None
    matched = None
    for pattern in pattern_list:
        if pattern.startswith('^'):
            # This is a regular expression match
            try:
                if re.search(pattern, email, re.IGNORECASE):
                    matched = pattern
                    break
            except re.error:
                # BAW: we should probably remove this pattern
                pass
        else:
            # Do the comparison case insensitively
            if pattern.lower() == email.lower():
                matched = pattern
                break
    return matched
