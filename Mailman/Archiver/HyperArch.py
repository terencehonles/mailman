# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
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

"""HyperArch: Pipermail archiving for Mailman

     - The Dragon De Monsyne <dragondm@integral.org>

   TODO:
     - Should be able to force all HTML to be regenerated next time the
       archive is run, in case a template is changed.
     - Run a command to generate tarball of html archives for downloading
       (probably in the 'update_dirty_archives' method).
"""

import sys
import re
import cgi
import urllib
import time
import os
import types
import HyperDatabase
import pipermail

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import LockFile
from Mailman import EncWord
from Mailman import i18n
from Mailman.Logging.Syslog import syslog
from Mailman.Mailbox import ArchiverMailbox

# Set up i18n.  Assume the current language has already been set in the caller.
_ = i18n._

gzip = None
if mm_cfg.GZIP_ARCHIVE_TXT_FILES:
    try:
        import gzip
    except ImportError:
        pass

EMPTYSTRING = ''
NL = '\n'



def unicode_quote(arg):
    if isinstance(arg, types.UnicodeType):
        result = []
        for c in arg:
            c = ord(c)
            if c < 128:
                result.append(chr(c))
            else:
                result.append("&#%d;" % c)
        arg = "".join(result)
    return arg


def html_quote(s):
    repls = ( ('&', '&amp;'),
              ("<", '&lt;'),
              (">", '&gt;'),
              ('"', '&quot;'))
    for thing, repl in repls:
        s = s.replace(thing, repl)
    return unicode_quote(s)


def url_quote(s):
    return urllib.quote(s)


def null_to_space(s):
    return s.replace('\000', ' ')


def sizeof(filename, lang):
    size = os.path.getsize(filename)
    if size < 1000:
        # Avoid i18n side-effects
        otrans = i18n.get_translation()
        try:
            i18n.set_language(lang)
            out = _(' %(size)i bytes ')
        finally:
            i18n.set_translation(otrans)
        return out
    elif size < 1000000:
        return ' %d KB ' % (size / 1000)
    # GB?? :-)
    return ' %d MB ' % (size / 1000000)


html_charset = '<META http-equiv="Content-Type" ' \
               'content="text/html; charset=%s">'

def CGIescape(arg):
    if isinstance(arg, types.UnicodeType):
        s = Utils.websafe(arg)
    else:
        s = Utils.websafe(str(arg))
    return unicode_quote(s.replace('"', '&quot;'))

# Parenthesized human name
paren_name_pat = re.compile(r'([(].*[)])')

# Subject lines preceded with 'Re:'
REpat = re.compile( r"\s*RE\s*(\[\d+\]\s*)?:\s*", re.IGNORECASE)

# E-mail addresses and URLs in text
emailpat = re.compile(r'([-+,.\w]+@[-+.\w]+)')

#  Argh!  This pattern is buggy, and will choke on URLs with GET parameters.
urlpat = re.compile(r'(\w+://[^>)\s]+)') # URLs in text

# Blank lines
blankpat = re.compile(r'^\s*$')

# Starting <html> directive
htmlpat = re.compile(r'^\s*<HTML>\s*$', re.IGNORECASE)
# Ending </html> directive
nohtmlpat = re.compile(r'^\s*</HTML>\s*$', re.IGNORECASE)
# Match quoted text
quotedpat = re.compile(r'^([>|:]|&gt;)+')


# Note: I'm overriding most, if not all of the pipermail Article class
#       here -ddm
# The Article class encapsulates a single posting.  The attributes are:
#
#  sequence : Sequence number, unique for each article in a set of archives
#  subject  : Subject
#  datestr  : The posting date, in human-readable format
#  date     : The posting date, in purely numeric format
#  fromdate : The posting date, in `unixfrom' format
#  headers  : Any other headers of interest
#  author   : The author's name (and possibly organization)
#  email    : The author's e-mail address
#  msgid    : A unique message ID
#  in_reply_to : If !="", this is the msgid of the article being replied to
#  references: A (possibly empty) list of msgid's of earlier articles in
#              the thread
#  body     : A list of strings making up the message body

class Article(pipermail.Article):
    __super_init = pipermail.Article.__init__
    __super_set_date = pipermail.Article._set_date

    _last_article_time = time.time()

    # Default
    charset = Utils.GetCharSet(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    def __init__(self, message=None, sequence=0, keepHeaders=[],
                       lang=mm_cfg.DEFAULT_SERVER_LANGUAGE, mlist=None):
        self.__super_init(message, sequence, keepHeaders)

        self.prev = None
        self.next = None

        # Trim Re: from the subject line
        i = 0
        while i != -1:
            result = REpat.match(self.subject)
            if result:
                i = result.end(0)
                self.subject = self.subject[i:]
            else:
                i = -1

        self._lang = lang
        self._mlist = mlist

        if mm_cfg.ARCHIVER_OBSCURES_EMAILADDRS:
            # Avoid i18n side-effects.  Note that the language for this
            # article (for this list) could be different from the site-wide
            # preferred language, so we need to ensure no side-effects will
            # occur.  Think what happens when executing bin/arch.
            otrans = i18n.get_translation()
            try:
                i18n.set_language(lang)
                self.email = re.sub('@', _(' at '), self.email)
            finally:
                i18n.set_translation(otrans)

        # Snag the content-* headers.  RFC 1521 states that their values are
        # case insensitive.
        ctype = message.get('Content-Type', 'text/plain')
        cenc = message.get('Content-Transfer-Encoding', '')
        self.ctype = ctype.lower()
        self.cenc = cenc.lower()
        self.decoded = {}
        charset = message.get_param('charset')
        if charset:
            charset = charset.lower().strip()
            if charset[0]=='"' and charset[-1]=='"':
                charset = charset[1:-1]
            if charset[0]=="'" and charset[-1]=="'":
                charset = charset[1:-1]
        self.check_header_charsets(charset)
        if self.charset and self.charset in mm_cfg.VERBATIM_ENCODING:
            self.quote = unicode_quote

    def __setstate__(self, d):
        # For loading older Articles via pickle.  All this stuff was added
        # when Simone Piunni and Tokio Kikuchi i18n'ified Pipermail.  See SF
        # patch #594771.
        self.__dict__ = d
        if not d.has_key('_mlist'):
            self._mlist = mlist = None
        if not d.has_key('_lang'):
            if mlist is not None:
                self._lang = lang = mlist.preferred_language
            else:
                self._lang = lang = mm_cfg.DEFAULT_SERVER_LANGUAGE
        if not d.has_key('charset'):
            self.charset = Utils.GetCharSet(lang)
        if not d.has_key('cenc'):
            self.cenc = None
        if not d.has_key('decoded'):
            self.decoded = {}

    def quote(self, buf):
        return html_quote(buf)

    def check_header_charsets(self, msg_charset=None):
        """Check From and Subject for encoded-words

        If the email, subject, or author attributes contain non-ASCII
        characters using the encoded-word syntax of RFC 2047, decoded
        versions of those attributes are placed in the self.decoded (a
        dictionary).

        If the charsets used by these headers differ from each other
        or from the charset specified by the message's Content-Type
        header, then an arbitrary charset is chosen. If the decoded
        fields match that charset, they are preserved
        literally. Otherwise, an attempt is made to decode them as
        Unicode. If that fails, they are left undecoded.
        """

        self.charset = msg_charset
        author, a_charset = self.decode_charset(self.author)
        if self.charset is None and a_charset:
            self.charset = a_charset
        subject, s_charset = self.decode_charset(self.subject)
        if self.charset is None and a_charset:
            self.charset = s_charset
        if author:
            self.decoded['author'] = author
            email, e_charset = self.decode_charset(self.email)
            if email:
                self.decoded['email'] = email
        if subject:
            self.decoded['subject'] = subject

    def decode_charset(self, field):
        if field.find("=?") == -1:
            return None, None
        try:
            s, c = EncWord.decode(field)
        except ValueError:
            return None, None
        c = c.lower()
        # If the charset of the header matches the article charset,
        # leave it as encoded. Otherwise, try Unicode decoding
        if c.lower() == self.charset:
            return s, c
        try:
            return unicode(s, c), None
        except (UnicodeError, LookupError):
            # Unknown encoding
            return None, None

    def as_html(self):
        d = self.__dict__.copy()

        # avoid i18n side-effects
        otrans = i18n.get_translation()
        i18n.set_language(self._lang)
        try:
            d["prev"], d["prev_wsubj"] = self._get_prev()
            d["next"], d["next_wsubj"] = self._get_next()

            d["email_html"] = self.quote(self.email)
            d["title"] = self.quote(self.subject)
            d["subject_html"] = self.quote(self.subject)
            d["subject_url"] = url_quote(self.subject)
            d["in_reply_to_url"] = url_quote(self.in_reply_to)
            d["author_html"] = self.quote(self.author)
            d["email_url"] = url_quote(self.email)
            d["datestr_html"] = self.quote(i18n.ctime(int(self.date)))
            d["body"] = self._get_body()
        finally:
            i18n.set_translation(otrans)

        if self.charset is not None:
            d["encoding"] = html_charset % self.charset
        else:
            d["encoding"] = ""

        self._add_decoded(d)
        return Utils.maketext(
             'article.html', d,
             raw=1, lang=self._lang, mlist=self._mlist)

    def _get_prev(self):
        """Return the href and subject for the previous message"""
        if self.prev:
            subject = self._get_subject_enc(self.prev)
            prev = ('<LINK REL="Previous"  HREF="%s">'
                    % (url_quote(self.prev.filename)))
            prev_wsubj = ('<LI>' + _('Previous message:') +
                          ' <A HREF="%s">%s\n</A></li>'
                          % (url_quote(self.prev.filename),
                             self.quote(subject)))
        else:
            prev = prev_wsubj = ""
        return prev, prev_wsubj

    def _get_subject_enc(self, art):
        """Return the subject of art, decoded if possible.

        If the charset of the current message and art match and the
        article's subject is encoded, decode it.
        """
        subj = art.decoded.get('subject')
        if not subj:
            return art.subject
        if isinstance(subj, types.UnicodeType):
            return subj
        if self.charset and self.charset == art.charset:
                return subj
        try:
            return unicode(subj, art.charset)
        except (UnicodeError, LookupError):
            return art.subject

    def _get_next(self):
        """Return the href and subject for the previous message"""
        if self.next:
            subject = self._get_subject_enc(self.next)
            next = ('<LINK REL="Next"  HREF="%s">'
                    % (url_quote(self.next.filename)))
            next_wsubj = ('<LI>' + _('Next message:') +
                          ' <A HREF="%s">%s\n</A></li>'
                          % (url_quote(self.next.filename),
                             self.quote(subject)))
        else:
            next = next_wsubj = ""
        return next, next_wsubj

    _rx_quote = re.compile('=([A-F0-9][A-F0-9])')
    _rx_softline = re.compile('=[ \t]*$')

    def _get_body(self):
        """Return the message body ready for HTML, decoded if necessary"""
        try:
            body = self.html_body
        except AttributeError:
            body = self.body
        if self.charset is None or self.cenc != "quoted-printable":
            return null_to_space(EMPTYSTRING.join(body))
        # the charset is specified and the body is quoted-printable
        # first get rid of soft line breaks, then decode literals
        lines = []
        rx = self._rx_softline
        for line in body:
            mo = rx.search(line)
            if mo:
                i = line.rfind("=")
                line = line[:i]
            lines.append(line)
        buf = EMPTYSTRING.join(lines)

        chunks = []
        offset = 0
        rx = self._rx_quote
        while 1:
            mo = rx.search(buf, offset)
            if not mo:
                chunks.append(buf[offset:])
                break
            i = mo.start()
            chunks.append(buf[offset:i])
            offset = i + 3
            chunks.append(chr(int(mo.group(1), 16)))
        return null_to_space(EMPTYSTRING.join(chunks))

    def _add_decoded(self, d):
        """Add encoded-word keys to HTML output"""
        for src, dst in (('author', 'author_html'),
                         ('email', 'email_html'),
                         ('subject', 'subject_html')):
            if self.decoded.has_key(src):
                d[dst] = self.quote(self.decoded[src])

    def as_text(self):
        d = self.__dict__.copy()
        # We need to guarantee a valid From_ line, even if there are
        # bososities in the headers.
        if not d.get('fromdate', '').strip():
            d['fromdate'] = time.ctime(time.time())
        if not d.get('email', '').strip():
            d['email'] = 'bogus@does.not.exist.com'
        if not d.get('datestr', '').strip():
            d['datestr'] = time.ctime(time.time())
        #
        headers = ['From %(email)s  %(fromdate)s',
                 'From: %(email)s (%(author)s)',
                 'Date: %(datestr)s',
                 'Subject: %(subject)s']
        if d['_in_reply_to']:
            headers.append('In-Reply-To: %(_in_reply_to)s')
        if d['_references']:
            headers.append('References: %(_references)s')
        if d['_message_id']:
            headers.append('Message-ID: %(_message_id)s')
        return NL.join(headers) % d + \
               '\n\n' + \
               EMPTYSTRING.join(self.body)

    def _set_date(self, message):
        self.__super_set_date(message)
        self.fromdate = time.ctime(int(self.date))

    def loadbody_fromHTML(self,fileobj):
        self.body = []
        begin = 0
        while 1:
            line = fileobj.readline()
            if not line:
                break
            if not begin:
                if line.strip() == '<!--beginarticle-->':
                    begin = 1
                continue
            if line.strip() == '<!--endarticle-->':
                break
            self.body.append(line)

    def __getstate__(self):
        d={}
        for each in self.__dict__.keys():
            if each == "quote":
                continue
            if each in ['maillist','prev','next','body']:
                d[each] = None
            else:
                d[each] = self.__dict__[each]
        d['body']=[]
        return d



class HyperArchive(pipermail.T):
    __super_init = pipermail.T.__init__
    __super_update_archive = pipermail.T.update_archive
    __super_update_dirty_archives = pipermail.T.update_dirty_archives
    __super_add_article = pipermail.T.add_article

    # some defaults
    DIRMODE = 02775
    FILEMODE = 0660

    VERBOSE = 0
    DEFAULTINDEX = 'thread'
    ARCHIVE_PERIOD = 'month'

    THREADLAZY = 0
    THREADLEVELS = 3

    ALLOWHTML = 1             # "Lines between <html></html>" handled as is.
    SHOWHTML = 0              # Eg, nuke leading whitespace in html manner.
    IQUOTES = 1               # Italicize quoted text.
    SHOWBR = 0                # Add <br> onto every line

    def __init__(self, maillist, unlock=1):
        # can't init the database while other processes are writing to it!
        # XXX TODO- implement native locking
        # with mailman's LockFile module for HyperDatabase.HyperDatabase
        #
        dir = maillist.archive_dir()
        db = HyperDatabase.HyperDatabase(dir)
        self.__super_init(dir, reload=1, database=db)

        self.maillist = maillist
        self._unlocklist = unlock
        self._lock_file = None
        self._charsets = {}
        self.charset = Utils.GetCharSet(maillist.preferred_language)

        if hasattr(self.maillist,'archive_volume_frequency'):
            if self.maillist.archive_volume_frequency == 0:
                self.ARCHIVE_PERIOD='year'
            elif self.maillist.archive_volume_frequency == 2:
                self.ARCHIVE_PERIOD='quarter'
            elif self.maillist.archive_volume_frequency == 3:
                self.ARCHIVE_PERIOD='week'
            elif self.maillist.archive_volume_frequency == 4:
                self.ARCHIVE_PERIOD='day'
            else:
                self.ARCHIVE_PERIOD='month'

        yre = r'(?P<year>[0-9]{4,4})'
        mre = r'(?P<month>[01][0-9])'
        dre = r'(?P<day>[0123][0-9])'
        self._volre = {
            'year':    '^' + yre + '$',
            'quarter': '^' + yre + r'q(?P<quarter>[1234])$',
            'month':   '^' + yre + r'-(?P<month>[a-zA-Z]+)$',
            'week':    r'^Week-of-Mon-' + yre + mre + dre,
            'day':     '^' + yre + mre + dre + '$'
            }

    def _makeArticle(self, msg, sequence):
        return Article(msg, sequence,
                       lang=self.maillist.preferred_language,
                       mlist=self.maillist)

    def html_foot(self):
        # avoid i18n side-effects
        mlist = self.maillist
        otrans = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            d = {"lastdate": html_quote(i18n.ctime(self.lastdate)),
                 "archivedate": html_quote(i18n.ctime(self.archivedate)),
                 "listinfo": mlist.GetScriptURL('listinfo', absolute=1),
                 "version": self.version,
                 }
            i = {"thread": _("thread"),
                 "subject": _("subject"),
                 "author": _("author"),
                 "date": _("date")
                 }
        finally:
            i18n.set_translation(otrans)

        for t in i.keys():
            cap = t[0].upper() + t[1:]
            if self.type == cap:
                d["%s_ref" % (t)] = ""
            else:
                d["%s_ref" % (t)] = ('<a href="%s.html#start">[ %s ]</a>'
                                     % (t, i[t]))
        return Utils.maketext(
            'archidxfoot.html', d, raw=1,
            lang=mlist.preferred_language,
            mlist=mlist)

    def html_head(self):
        # avoid i18n side-effects
        mlist = self.maillist
        otrans = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            d = {"listname": html_quote(mlist.real_name),
                 "archtype": self.type,
                 "archive":  self.volNameToDesc(self.archive),
                 "listinfo": mlist.GetScriptURL('listinfo', absolute=1),
                 "firstdate": html_quote(i18n.ctime(self.firstdate)),
                 "lastdate": html_quote(i18n.ctime(self.lastdate)),
                 "size": self.size,
                 }
            i = {"thread": _("thread"),
                 "subject": _("subject"),
                 "author": _("author"),
                 "date": _("date"),
                 }
        finally:
            i18n.set_translation(otrans)

        for t in i.keys():
            cap = t[0].upper() + t[1:]
            if self.type == cap:
                d["%s_ref" % (t)] = ""
                d["archtype"] = i[t]
            else:
                d["%s_ref" % (t)] = ('<a href="%s.html#start">[ %s ]</a>'
                                     % (t, i[t]))
        if self.charset:
            d["encoding"] = html_charset % self.charset
        else:
            d["encoding"] = ""
        return Utils.maketext(
            'archidxhead.html', d, raw=1,
            lang=mlist.preferred_language,
            mlist=mlist)

    def html_TOC(self):
        mlist = self.maillist
        listname = mlist.internal_name()
        mbox = os.path.join(mlist.archive_dir()+'.mbox', listname+'.mbox')
        d = {"listname": mlist.real_name,
             "listinfo": mlist.GetScriptURL('listinfo', absolute=1),
             "fullarch": '../%s.mbox/%s.mbox' % (listname, listname),
             "size": sizeof(mbox, mlist.preferred_language),
             }
        # Avoid i18n side-effects
        otrans = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            if not self.archives:
                d["noarchive_msg"] = _(
                    '<P>Currently, there are no archives. </P>')
                d["archive_listing_start"] = ""
                d["archive_listing_end"] = ""
                d["archive_listing"] = ""
            else:
                d["noarchive_msg"] = ""
                d["archive_listing_start"] = Utils.maketext(
                    'archliststart.html', raw=1,
                    lang=mlist.preferred_language,
                    mlist=mlist)
                d["archive_listing_end"] = Utils.maketext(
                    'archlistend.html', raw=1,
                    lang=mlist.preferred_language,
                    mlist=mlist)

                accum = []
                for a in self.archives:
                    accum.append(self.html_TOC_entry(a))
                d["archive_listing"] = EMPTYSTRING.join(accum)
        finally:
            i18n.set_translation(otrans)

        if not d.has_key("encoding"):
            d["encoding"] = ""

        return Utils.maketext(
            'archtoc.html', d, raw=1,
            lang=mlist.preferred_language,
            mlist=mlist)

    def html_TOC_entry(self, arch):
        # Check to see if the archive is gzip'd or not
        txtfile = os.path.join(self.maillist.archive_dir(), arch + '.txt')
        gzfile = txtfile + '.gz'
        # which exists?  .txt.gz first, then .txt
        if os.path.exists(gzfile):
            file = gzfile
            url = arch + '.txt.gz'
            templ = '<td><A href="%(url)s">[ ' + _('Gzip\'d Text%(sz)s') \
                    + ']</a></td>'
        elif os.path.exists(txtfile):
            file = txtfile
            url = arch + '.txt'
            templ = '<td><A href="%(url)s">[ ' + _('Text%(sz)s') + ']</a></td>'
        else:
            # neither found?
            file = None
        # in Python 1.5.2 we have an easy way to get the size
        if file:
            textlink = templ % {
                'url': url,
                'sz' : sizeof(file, self.maillist.preferred_language)
                }
        else:
            # there's no archive file at all... hmmm.
            textlink = ''
        return Utils.maketext(
            'archtocentry.html',
            {'archive': arch,
             'archivelabel': self.volNameToDesc(arch),
             'textlink': textlink
             },
            raw=1, lang=self.maillist.preferred_language, mlist=self.maillist)

    def GetArchLock(self):
        if self._lock_file:
            return 1
        self._lock_file = LockFile.LockFile(
            os.path.join(mm_cfg.LOCK_DIR,
                         self.maillist.internal_name() + '-arch.lock'))
        try:
            self._lock_file.lock(timeout=0.5)
        except LockFile.TimeOutError:
            return 0
        return 1

    def DropArchLock(self):
        if self._lock_file:
            self._lock_file.unlock(unconditionally=1)
            self._lock_file = None

    def processListArch(self):
        name = self.maillist.ArchiveFileName()
        wname= name+'.working'
        ename= name+'.err_unarchived'
        try:
            os.stat(name)
        except (IOError,os.error):
            #no archive file, nothin to do -ddm
            return

        #see if arch is locked here -ddm
        if not self.GetArchLock():
            #another archiver is running, nothing to do. -ddm
            return

        #if the working file is still here, the archiver may have
        # crashed during archiving. Save it, log an error, and move on.
        try:
            wf = open(wname)
            syslog('error',
                   'Archive working file %s present.  '
                   'Check %s for possibly unarchived msgs',
                   wname, ename)
            omask = os.umask(007)
            try:
                ef = open(ename, 'a+')
            finally:
                os.umask(omask)
            ef.seek(1,2)
            if ef.read(1) <> '\n':
                ef.write('\n')
            ef.write(wf.read())
            ef.close()
            wf.close()
            os.unlink(wname)
        except IOError:
            pass
        os.rename(name,wname)
        if self._unlocklist:
            self.maillist.Unlock()
        archfile = open(wname)
        self.processUnixMailbox(archfile)
        archfile.close()
        os.unlink(wname)
        self.DropArchLock()

    def get_filename(self, article):
        return '%06i.html' % (article.sequence,)

    def get_archives(self, article):
        """Return a list of indexes where the article should be filed.
        A string can be returned if the list only contains one entry,
        and the empty list is legal."""
        res = self.dateToVolName(float(article.date))
        self.message(_("figuring article archives\n"))
        self.message(res + "\n")
        return res

    def volNameToDesc(self, volname):
        volname = volname.strip()
        # Don't make these module global constants since we have to runtime
        # translate them anyway.
        monthdict = [
            '',
            _('January'),   _('February'), _('March'),    _('April'),
            _('May'),       _('June'),     _('July'),     _('August'),
            _('September'), _('October'),  _('November'), _('December')
            ]
        for each in self._volre.keys():
            match = re.match(self._volre[each], volname)
            # Let ValueErrors percolate up
            if match:
                year = int(match.group('year'))
                if each == 'quarter':
                    d =["", _("First"), _("Second"), _("Third"), _("Fourth") ]
                    ord = d[int(match.group('quarter'))]
                    return _("%(ord)s quarter %(year)i")
                elif each == 'month':
                    monthstr = match.group('month').lower()
                    for i in range(1, 13):
                        monthname = time.strftime("%B", (1999,i,1,0,0,0,0,1,0))
                        if monthstr.lower() == monthname.lower():
                            month = monthdict[i]
                            return _("%(month)s %(year)i")
                    raise ValueError, "%s is not a month!" % monthstr
                elif each == 'week':
                    month = monthdict[int(match.group("month"))]
                    day = int(match.group("day"))
                    return _("The Week Of Monday %(day)i %(month)s %(year)i")
                elif each == 'day':
                    month = monthdict[int(match.group("month"))]
                    day = int(match.group("day"))
                    return _("%(day)i %(month)s %(year)i")
                else:
                    return match.group('year')
        raise ValueError, "%s is not a valid volname" % volname

# The following two methods should be inverses of each other. -ddm

    def dateToVolName(self,date):
        datetuple=time.localtime(date)
        if self.ARCHIVE_PERIOD=='year':
            return time.strftime("%Y",datetuple)
        elif self.ARCHIVE_PERIOD=='quarter':
            if datetuple[1] in [1,2,3]:
                return time.strftime("%Yq1",datetuple)
            elif datetuple[1] in [4,5,6]:
                return time.strftime("%Yq2",datetuple)
            elif datetuple[1] in [7,8,9]:
                return time.strftime("%Yq3",datetuple)
            else:
                return time.strftime("%Yq4",datetuple)
        elif self.ARCHIVE_PERIOD == 'day':
            return time.strftime("%Y%m%d", datetuple)
        elif self.ARCHIVE_PERIOD == 'week':
            # Reconstruct "seconds since epoch", and subtract weekday
            # multiplied by the number of seconds in a day.
            monday = time.mktime(datetuple) - datetuple[6] * 24 * 60 * 60
            # Build a new datetuple from this "seconds since epoch" value
            datetuple = time.localtime(monday)
            return time.strftime("Week-of-Mon-%Y%m%d", datetuple)
        # month. -ddm
        else:
            return time.strftime("%Y-%B",datetuple)


    def volNameToDate(self,volname):
        volname = volname.strip()
        for each in self._volre.keys():
            match=re.match(self._volre[each],volname)
            if match:
                year=int(match.group('year'))
                month=1
                day = 1
                if each == 'quarter':
                    q=int(match.group('quarter'))
                    month=(q*3)-2
                elif each == 'month':
                    monthstr=match.group('month').lower()
                    m=[]
                    for i in range(1,13):
                        m.append(
                            time.strftime("%B",(1999,i,1,0,0,0,0,1,0)).lower())
                    try:
                        month=m.index(monthstr)+1
                    except ValueError:
                        pass
                elif each == 'week' or each == 'day':
                    month = int(match.group("month"))
                    day = int(match.group("day"))
                return time.mktime((year,month,1,0,0,0,0,1,-1))
        return 0.0

    def sortarchives(self):
        def sf(a,b,s=self):
            al=s.volNameToDate(a)
            bl=s.volNameToDate(b)
            if al>bl:
                return 1
            elif al<bl:
                return -1
            else:
                return 0
        if self.ARCHIVE_PERIOD in ('month','year','quarter'):
            self.archives.sort(sf)
        else:
            self.archives.sort()
        self.archives.reverse()

    def message(self, msg):
        if self.VERBOSE:
            f = sys.stderr
            f.write(msg)
            if msg[-1:] != '\n':
                f.write('\n')
            f.flush()

    def open_new_archive(self, archive, archivedir):
        index_html = os.path.join(archivedir, 'index.html')
        try:
            os.unlink(index_html)
        except:
            pass
        os.symlink(self.DEFAULTINDEX+'.html',index_html)

    def write_index_header(self):
        self.depth=0
        print self.html_head()
        if not self.THREADLAZY and self.type=='Thread':
            self.message(_("Computing threaded index\n"))
            self.updateThreadedIndex()

    def write_index_footer(self):
        for i in range(self.depth): print '</UL>'
        print self.html_foot()

    def write_index_entry(self, article):
        subject = self.get_header("subject", article)
        author = self.get_header("author", article)
        subject = CGIescape(subject)
        author = CGIescape(author)

        d = {
            'filename': urllib.quote(article.filename),
            'subject':  subject,
            'sequence': article.sequence,
            'author':   author
        }
        print Utils.maketext(
            'archidxentry.html', d, raw=1,
            lang=self.maillist.preferred_language,
            mlist=self.maillist)

    def get_header(self, field, article):
        # if we have no decoded header, return the encoded one
        result = article.decoded.get(field)
        if result is None:
            return getattr(article, field)
        # if the encodings match, use the result
        if self.charset == article.charset:
            return result
        # otherwise, try to return a Unicode result
        if isinstance(result, types.UnicodeType):
            return result
        try:
            return unicode(result, article.charset)
        except (UnicodeError, LookupError):
            return getattr(article, field)

    def write_threadindex_entry(self, article, depth):
        if depth < 0:
            self.message('depth<0')
            depth = 0
        if depth > self.THREADLEVELS:
            depth = self.THREADLEVELS
        if depth < self.depth:
            for i in range(self.depth-depth):
                print '</UL>'
        elif depth > self.depth:
            for i in range(depth-self.depth):
                print '<UL>'
        print '<!--%i %s -->' % (depth, article.threadKey)
        self.depth = depth
        self.write_index_entry(article)

    def write_TOC(self):
        self.sortarchives()
        omask = os.umask(002)
        try:
            toc = open(os.path.join(self.basedir, 'index.html'), 'w')
        finally:
            os.umask(omask)
        toc.write(self.html_TOC())
        toc.close()

    def write_article(self, index, article, path):
        # called by add_article
        omask = os.umask(002)
        try:
            f = open(path, 'w')
        finally:
            os.umask(omask)
        f.write(article.as_html())
        f.close()

        # Write the text article to the text archive.
        path = os.path.join(self.basedir, "%s.txt" % index)
        omask = os.umask(002)
        try:
            f = open(path, 'a+')
        finally:
            os.umask(omask)
        f.write(article.as_text())
        f.close()

    def add_article(self, article):
        self.__super_add_article(article)
        if article.charset:
            cs = article.charset
            self._charsets[cs] = self._charsets.get(cs, 0) + 1

    def choose_charset(self):
        """Pick a charset for the index files

        This method choose the most frequently occuring charset in the
        individual messages.

        XXX There should be an option to set a default charset.
        """
        if not self._charsets:
            return
        l = map(lambda p:(p[1], p[0]), self._charsets.items())
        l.sort() # largest last
        self.charset = l[-1][1]

    def update_dirty_archives(self):
        self.choose_charset()
        self.__super_update_dirty_archives()

    def update_archive(self, archive):
        self.__super_update_archive(archive)
        # only do this if the gzip module was imported globally, and
        # gzip'ing was enabled via mm_cfg.GZIP_ARCHIVE_TXT_FILES.  See
        # above.
        if gzip:
            archz = None
            archt = None
            txtfile = os.path.join(self.basedir, '%s.txt' % archive)
            gzipfile = os.path.join(self.basedir, '%s.txt.gz' % archive)
            oldgzip = os.path.join(self.basedir, '%s.old.txt.gz' % archive)
            try:
                # open the plain text file
                archt = open(txtfile)
            except IOError:
                return
            try:
                os.rename(gzipfile, oldgzip)
                archz = gzip.open(oldgzip)
            except (IOError, RuntimeError, os.error):
                pass
            try:
                ou = os.umask(002)
                newz = gzip.open(gzipfile, 'w')
            finally:
                # XXX why is this a finally?
                os.umask(ou)
            if archz:
                newz.write(archz.read())
                archz.close()
                os.unlink(oldgzip)
            # XXX do we really need all this in a try/except?
            try:
                newz.write(archt.read())
                newz.close()
                archt.close()
            except IOError:
                pass
            os.unlink(txtfile)

    _skip_attrs = ('maillist', '_lock_file', '_unlocklist',
                   'charset')

    def getstate(self):
        d={}
        for each in self.__dict__.keys():
            if not (each in self._skip_attrs
                    or each.upper() == each):
                d[each] = self.__dict__[each]
        return d

    # Add <A HREF="..."> tags around URLs and e-mail addresses.

    def __processbody_URLquote(self, lines):
        # XXX a lot to do here:
        # 1. use lines directly, rather than source and dest
        # 2. make it clearer
        # 3. make it faster
        source = lines[:]
        dest = lines
        body2=[]
        last_line_was_quoted=0
        for i in xrange(0, len(source)):
            Lorig=L=source[i] ; prefix=suffix=""
            if L==None: continue
            # Italicise quoted text
            if self.IQUOTES:
                quoted=quotedpat.match(L)
                if quoted==None: last_line_was_quoted=0
                else:
                    quoted = quoted.end(0)
                    prefix=CGIescape(L[:quoted]) + '<i>'
                    suffix='</I>'
                    if self.SHOWHTML:
                        suffix=suffix+'<BR>'
                        if not last_line_was_quoted:
                            prefix='<BR>'+prefix
                    L= L[quoted:]
                    last_line_was_quoted=1
            # Check for an e-mail address
            L2="" ; jr=emailpat.search(L) ; kr=urlpat.search(L)
            while jr!=None or kr!=None:
                if jr==None: j=-1
                else: j = jr.start(0)
                if kr==None: k=-1
                else: k = kr.start(0)
                if j!=-1 and (j<k or k==-1):
                    text=jr.group(1) ; URL='mailto:'+text ; pos=j
                elif k!=-1 and (j>k or j==-1): text=URL=kr.group(1) ; pos=k
                else: # j==k
                    raise ValueError, "j==k: This can't happen!"
                length=len(text)
                #self.message("URL: %s %s %s \n"
                #             % (CGIescape(L[:pos]), URL, CGIescape(text)))
                L2 = L2 + ('%s<A HREF="%s">%s</A>'
                           % (CGIescape(L[:pos]), URL, CGIescape(text)))
                L=L[pos+length:]
                jr=emailpat.search(L) ; kr=urlpat.search(L)
            if jr==None and kr==None: L=CGIescape(L)
            L=prefix+L2+L+suffix
            if L!=Lorig: source[i], dest[i]=None, L

    # Perform Hypermail-style processing of <HTML></HTML> directives
    # in message bodies.  Lines between <HTML> and </HTML> will be written
    # out precisely as they are; other lines will be passed to func2
    # for further processing .

    def __processbody_HTML(self, lines):
        # XXX need to make this method modify in place
        source = lines[:]
        dest = lines
        l = len(source)
        i = 0
        while i < l:
            while i < l and htmlpat.match(source[i]) is None:
                i = i + 1
            if i < l:
                source[i] = None
                i = i + 1
            while i < l and nohtmlpat.match(source[i]) is None:
                dest[i], source[i] = source[i], None
                i = i + 1
            if i < l:
                source[i] = None
                i = i + 1

    def format_article(self, article):
        # called from add_article
        # TBD: Why do the HTML formatting here and keep it in the
        # pipermail database?  It makes more sense to do the html
        # formatting as the article is being written as html and toss
        # the data after it has been written to the archive file.
        lines = filter(None, article.body)
        # Handle <HTML> </HTML> directives
        if self.ALLOWHTML:
            self.__processbody_HTML(lines)
        self.__processbody_URLquote(lines)
        if not self.SHOWHTML and lines:
            lines.insert(0, '<PRE>')
            lines.append('</PRE>')
        else:
            # Do fancy formatting here
            if self.SHOWBR:
                lines = map(lambda x:x + "<BR>", lines)
            else:
                for i in range(0, len(lines)):
                    s = lines[i]
                    if s[0:1] in ' \t\n':
                        lines[i] = '<P>' + s
        article.html_body = lines
        return article

    def update_article(self, arcdir, article, prev, next):
        self.message(_('Updating HTML for article ') + str(article.sequence))
        try:
            f = open(os.path.join(arcdir, article.filename))
            article.loadbody_fromHTML(f)
            f.close()
        except IOError:
            self.message(_("article file %s is missing!")
                         % os.path.join(arcdir, article.filename))
        article.prev = prev
        article.next = next
        omask = os.umask(002)
        try:
            f = open(os.path.join(arcdir, article.filename), 'w')
        finally:
            os.umask(omask)
        f.write(article.as_html())
        f.close()
