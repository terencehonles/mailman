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

"""HyperArch:  Pipermail archiving for MailMan

       - The Dragon De Monsyne <dragondm@integral.org> 

   TODO:
     - The templates should be be files in Mailman's Template dir, instead
       of static strings.
     - Each list should be able to have it's own templates.
       Also, it should automatically fall back to default template in case 
       of error in list specific template. 
     - Should be able to force all HTML to be regenerated next time the archive
       is run, incase a template is changed. 
     - Run a command to generate tarball of html archives for downloading
       (prolly in the 'update_dirty_archives' method )

"""   

import sys
import re
import cgi
import urllib
import string
import time
import pickle
import os
import posixfile
import HyperDatabase
import pipermail

from Mailman import mm_cfg, EncWord
from Mailman.Logging.Syslog import syslog

from Mailman.Utils import mkdir, open_ex

gzip = None
if mm_cfg.GZIP_ARCHIVE_TXT_FILES:
    try:
        import gzip
    except ImportError:
        pass


def html_quote(s):
    repls = ( ('&', '&amp;'),
	      ("<", '&lt;'),
	      (">", '&gt;'),
	      ('"', '&quot;'))
    for thing, repl in repls:
	s = string.replace(s, thing, repl)
    return s

def url_quote(s):
    return urllib.quote(s)


article_text_template="""\
From %(email)s  %(fromdate)s
Date: %(datestr)s
From: %(author)s %(email)s
Subject: %(subject)s

%(body)s

"""

article_template='''\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
 <HEAD>
   <TITLE> %(title)s
   </TITLE>
   <LINK REL="Index" HREF="index.html" >
   <LINK REL="made" HREF="mailto:%(email_url)s">
   %(encoding)s
   %(prev)s
   %(next)s
 </HEAD>
 <BODY BGCOLOR="#ffffff">
   <H1>%(subject_html)s
   </H1>
    <B>%(author_html)s
    </B> 
    <A HREF="mailto:%(email_url)s"
       TITLE="%(subject_html)s">%(email_html)s
       </A><BR>
    <I>%(datestr_html)s</I>
    <P><UL>
        %(prev_wsubj)s
        %(next_wsubj)s
         <LI> <B>Messages sorted by:</B> 
              <a href="date.html#%(sequence)s">[ date ]</a>
              <a href="thread.html#%(sequence)s">[ thread ]</a>
              <a href="subject.html#%(sequence)s">[ subject ]</a>
              <a href="author.html#%(sequence)s">[ author ]</a>
         </LI>
       </UL>
    <HR>  
<!--beginarticle-->
%(body)s
<!--endarticle-->
    <HR>
    <P><UL>
        <!--threads-->
	%(prev_wsubj)s
	%(next_wsubj)s
         <LI> <B>Messages sorted by:</B> 
              <a href="date.html#%(sequence)s">[ date ]</a>
              <a href="thread.html#%(sequence)s">[ thread ]</a>
              <a href="subject.html#%(sequence)s">[ subject ]</a>
              <a href="author.html#%(sequence)s">[ author ]</a>
         </LI>
       </UL>
</body></html>
'''

html_charset = '<META http-equiv="Content-Type" ' \
               'content="text/html; charset=%s">'

def CGIescape(arg): 
    s = cgi.escape(str(arg))
    s = re.sub('"', '&quot;', s)
    return s

# Parenthesized human name
paren_name_pat = re.compile(r'([(].*[)])') 

# Subject lines preceded with 'Re:' 
REpat = re.compile( r"\s*RE\s*:\s*", re.IGNORECASE)

# E-mail addresses and URLs in text
emailpat = re.compile(r'([-+,.\w]+@[-+.\w]+)') 

#  Argh!  This pattern is buggy, and will choke on URLs with GET parameters.
urlpat = re.compile(r'(\w+://[^>)\s]+)') # URLs in text

# Blank lines
blankpat = re.compile(r'^\s*$')

# content-type charset
rx_charset = re.compile('charset="(\w+)"')

# 
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
#	       the thread 
#  body     : A list of strings making up the message body

class Article(pipermail.Article):
    __super_init = pipermail.Article.__init__
    __super_set_date = pipermail.Article._set_date
    
    _last_article_time = time.time()

    html_tmpl = article_template
    text_tmpl = article_text_template

    # for compatibility with old archives loaded via pickle
    charset = None
    cenc = None
    decoded = {}

    def __init__(self, message=None, sequence=0, keepHeaders=[]):
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

        if mm_cfg.ARCHIVER_OBSCURES_EMAILADDRS:
            self.email = re.sub('@', ' at ', self.email)

        # snag the content-type
        self.ctype = message.getheader('Content-Type') or "text/plain"
        self.cenc = message.getheader('Content-Transfer-Encoding')
        self.decoded = {}
        mo = rx_charset.search(self.ctype)
        if mo:
            self.check_header_charsets(string.lower(mo.group(1)))
        else:
            self.check_header_charsets()
        if self.charset:
            assert self.charset == string.lower(self.charset), \
                   self.charset

    def check_header_charsets(self, msg_charset=None):
        """Check From and Subject for encoded-words

        If the email, subject, or author attributes contain non-ASCII
        characters using the encoded-word syntax of RFC 2047, decoded
        versions of those attributes are placed in the self.decoded (a
        dictionary).

        If the charsets used by these headers differ from each other
        or from the charset specified by the message's Content-Type
        header, then an arbitrary charset is chosen.  Only those
        values that match the chosen charset are decoded.
        """
        author, a_charset = self.decode_charset(self.author)
        subject, s_charset = self.decode_charset(self.subject)
        if author is not None or subject is not None:
            # Both charsets should be the same.  If they aren't, we
            # can only handle one way.
            if msg_charset is None:
                self.charset = a_charset or s_charset
            else:
                self.charset = msg_charset

            if author and self.charset == a_charset:
                self.decoded['author'] = author
                email, e_charset = self.decode_charset(self.email)
                if email:
                    self.decoded['email'] = email
            if subject and self.charset == s_charset:
                self.decoded['subject'] = subject

    def decode_charset(self, field):
        if string.find(field, "=?") == -1:
            return None, None
        try:
            s, c = EncWord.decode(field)
        except ValueError:
            return None, None
        return s, string.lower(c)

    def as_html(self):
	d = self.__dict__.copy()
	if self.prev:
	    d["prev"] = ('<LINK REL="Previous"  HREF="%s">'
                         % (url_quote(self.prev.filename)))
	    d["prev_wsubj"] = ('<LI> Previous message:'
                               ' <A HREF="%s">%s</A></li>'
                               % (url_quote(self.prev.filename),
                                  html_quote(self.prev.subject)))
	else:
	    d["prev"] = d["prev_wsubj"] = ""
	    
	if self.next:
	    d["next"] = ('<LINK REL="Next" HREF="%s">'
                         % (html_quote(self.next.filename)))
	    d["next_wsubj"] = ('<LI> Next message: <A HREF="%s">%s</A></li>'
                               % (url_quote(self.next.filename),
                                  html_quote(self.next.subject)))
	else:
	    d["next"] = d["next_wsubj"] = ""
	
	d["email_html"] = html_quote(self.email)
	d["title"] = html_quote(self.subject)
	d["subject_html"] = html_quote(self.subject)
	d["author_html"] = html_quote(self.author)
	d["email_url"] = url_quote(self.email)
	d["datestr_html"] = html_quote(self.datestr)
        d["body"] = self._get_body()

        if self.charset is not None:
            d["encoding"] = html_charset % self.charset
        else:
            d["encoding"] = ""

        self._add_decoded(d)
            
        return self.html_tmpl % d

    _rx_quote = re.compile('=([A-Z0-9][A-Z0-9])')
    _rx_softline = re.compile('=[ \t]*$')

    def _get_body(self):
        """Return the message body ready for HTML, decoded if necessary"""
        if self.charset is None or self.cenc != "quoted-printable":
            return string.join(self.body, "")
        # the charset is specified and the body is quoted-printable
        # first get rid of soft line breaks, then decode literals
        lines = []
        rx = self._rx_softline
        for line in self.body:
            mo = rx.search(line)
            if mo:
                i = string.rfind(line, "=")
                line = line[:i]
            lines.append(line)
        buf = string.join(lines, "")
        
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
        return string.join(chunks, "")

    def _add_decoded(self, d):
        """Add encoded-word keys to HTML output"""
        for src, dst in (('author', 'author_html'),
                         ('email', 'email_html'),
                         ('subject', 'subject_html')):
            if self.decoded.has_key(src):
                d[dst] = self.decoded[src]
    
    def as_text(self):
	d = self.__dict__.copy()
	d["body"] = string.join(self.body, "")
        return self.text_tmpl % d

    def _set_date(self, message):
        self.__super_set_date(message)
        self.fromdate = time.ctime(int(self.date))
	
    def loadbody_fromHTML(self,fileobj):
        self.body=[]
        begin=0
	while(1):
            line=fileobj.readline()
            if not line:
                break
            if (not begin) and string.strip(line)=='<!--beginarticle-->':
	        begin=1
                continue
            if string.strip(line)=='<!--endarticle-->':
                break
            if begin:
                self.body.append(line)

    def __getstate__(self):
        d={}
        for each in self.__dict__.keys():
            if each in ['maillist','prev','next','body']:
                d[each] = None
            else:
                d[each] = self.__dict__[each]
        d['body']=[]
        return d


#
# Archive class specific stuff
#
index_header_template='''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
  <HEAD>
     <title>The %(listname)s %(archive)s Archive by %(archtype)s</title>
     %(encoding)s
  </HEAD>
  <BODY BGCOLOR="#ffffff">
      <a name="start"></A>
      <h1>%(archive)s Archives by %(archtype)s</h1>
      <ul>
         <li> <b>Messages sorted by:</b>
	        %(thread_ref)s
		%(subject_ref)s
		%(author_ref)s
		%(date_ref)s

	     <li><b><a href="%(listinfo)s">More info on this list...
                    </a></b></li>
      </ul>
      <p><b>Starting:</b> <i>%(firstdate)s</i><br>
         <b>Ending:</b> <i>%(lastdate)s</i><br>
         <b>Messages:</b> %(size)s<p>
     <ul>
'''

index_entry_template = \
"""<LI><A HREF="%s">%s
</A><A NAME="%i">&nbsp;</A>
<I>%s
</I>"""

index_footer_template='''\
    </ul>
    <p>
      <a name="end"><b>Last message date:</b></a> 
       <i>%(lastdate)s</i><br>
    <b>Archived on:</b> <i>%(archivedate)s</i>
    <p>
   <ul>
         <li> <b>Messages sorted by:</b>
	        %(thread_ref)s
		%(subject_ref)s
		%(author_ref)s
		%(date_ref)s
	     <li><b><a href="%(listinfo)s">More info on this list...
                    </a></b></li>
     </ul>
     <p>
     <hr>
     <i>This archive was generated by
     Pipermail %(version)s.</i>
  </BODY>
</HTML>
'''

TOC_template='''\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
  <HEAD>
     <title>The %(listname)s Archives</title>
  </HEAD>
  <BODY BGCOLOR="#ffffff">
     <h1>The %(listname)s Archives </h1>
     <p>
      <a href="%(listinfo)s">More info on this list...</a>
     </p>
     %(noarchive_msg)s
     %(archive_listing_start)s
     %(archive_listing)s
     %(archive_listing_end)s
     </BODY>
     </HTML>
'''

TOC_entry_template = '''\

	    <tr>
            <td>%(archive)s:</td>
            <td>
              <A href="%(archive)s/thread.html">[ Thread ]</a>
              <A href="%(archive)s/subject.html">[ Subject ]</a>
              <A href="%(archive)s/author.html">[ Author ]</a>
              <A href="%(archive)s/date.html">[ Date ]</a>
            </td>
            %(textlink)s
            </tr>

'''
arch_listing_start = '''\
	<table border=3>
          <tr><td>Archive</td>
          <td>View by:</td>
          <td>Downloadable version</td></tr>
'''

arch_listing_end = '''\
         </table>
'''
 

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
        self.charset = None

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

    html_hdr_tmpl = index_header_template
    html_foot_tmpl = index_footer_template
    html_TOC_tmpl = TOC_template
    TOC_entry_tmpl = TOC_entry_template    
    arch_listing_start = arch_listing_start
    arch_listing_end = arch_listing_end

    def html_foot(self):
	d = {"lastdate": html_quote(self.lastdate),
	     "archivedate": html_quote(self.archivedate),
	     "listinfo": self.maillist.GetScriptURL('listinfo', absolute=1),
	     "version": self.version}
	for t in ("thread", "subject", "author", "date"):
	    cap = string.upper(t[0]) + t[1:]
	    if self.type == cap:
		d["%s_ref" % (t)] = ""
	    else:
		d["%s_ref" % (t)] = ('<a href="%s.html#start">[ %s ]</a>'
                                     % (t, t))
        return self.html_foot_tmpl % d


    def html_head(self):
	d = {"listname": html_quote(self.maillist.real_name),
	     "archtype": self.type,
	     "archive": self.archive,
	     "listinfo": self.maillist.GetScriptURL('listinfo', absolute=1),
	     "firstdate": html_quote(self.firstdate),
	     "lastdate": html_quote(self.lastdate),
	     "size": self.size,
	     }
	for t in ("thread", "subject", "author", "date"):
	    cap = string.upper(t[0]) + t[1:]
	    if self.type == cap:
		d["%s_ref" % (t)] = ""
	    else:
		d["%s_ref" % (t)] = ('<a href="%s.html#start">[ %s ]</a>'
                                     % (t, t))
        if self.charset:
            d["encoding"] = html_charset % self.charset
        else:
            d["encoding"] = ""
        return self.html_hdr_tmpl % d

    def html_TOC(self):
        d = {"listname": self.maillist.real_name,
             "listinfo": self.maillist.GetScriptURL('listinfo', absolute=1)
             }
        if not self.archives:
            d["noarchive_msg"] = '<P>Currently, there are no archives. </P>'
            d["archive_listing_start"] = ""
            d["archive_listing_end"] = ""
            d["archive_listing"] = ""
        else:
            d["noarchive_msg"] = ""
            d["archive_listing_start"] = self.arch_listing_start
            d["archive_listing_end"] = self.arch_listing_end
            accum = []
            for a in self.archives:
                accum.append(self.html_TOC_entry(a))
        d["archive_listing"] = string.join(accum, '')
        if not d.has_key("encoding"):
            d["encoding"] = ""
        return self.html_TOC_tmpl % d

    def html_TOC_entry(self, arch):
        # Check to see if the archive is gzip'd or not
        txtfile = os.path.join(mm_cfg.PRIVATE_ARCHIVE_FILE_DIR,
                               self.maillist.internal_name(),
                               arch + '.txt')
        gzfile = txtfile + '.gz'
        templ = '<td><A href="%(url)s">[ %(fmt)sText%(sz)s]</a></td>'
        # which exists?  .txt.gz first, then .txt
        if os.path.exists(gzfile):
            file = gzfile
            url = arch + '.txt.gz'
            fmt = "Gzip'd "
        elif os.path.exists(txtfile):
            file = txtfile
            url = arch + '.txt'
            fmt = ''
        else:
            # neither found?
            file = None
        # in Python 1.5.2 we have an easy way to get the size
        if file:
            try:
                size = os.path.getsize(file)
            except AttributeError:
                # getsize() probably does this anyway ;-)
                size = os.stat(file)[6]
            if size < 1000:
                sz = ' %d bytes ' % size
            elif size < 1000000:
                sz = ' %d KB ' % (size / 1000)
            else:
                sz = ' %d MB ' % (size / 1000000)
                # GB?? :-)
            textlink = templ % {'url': url,
                                'fmt': fmt,
                                'sz' : sz}
        else:
            # there's no archive file at all... hmmm.
            textlink = ''
        return self.TOC_entry_tmpl % { 'archive': arch,
                                       'textlink': textlink }

    def GetArchLock(self):
        if self._lock_file:
            return 1
        # TBD: This needs to be rewritten to use the generalized locking
        # mechanism (when that exists).  -baw
        ou = os.umask(0)
        try:
            self._lock_file = posixfile.open(
                os.path.join(mm_cfg.LOCK_DIR, '%s@arch.lock'
                             % self.maillist.internal_name()), 'a+')
        finally:
            os.umask(ou)
        # minor race condition here, there is no way to atomicly 
        # check & get a lock. That shouldn't matter here tho' -ddm
        if not self._lock_file.lock('w?', 1):
            self._lock_file.lock('w|', 1)
        else:
            return 0
        return 1

    def DropArchLock(self):
        if self._lock_file:
            self._lock_file.lock('u')
            self._lock_file.close()
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
            wf=open_ex(wname,'r')
            syslog("error","Archive working file %s present. "
                   "Check %s for possibly unarchived msgs"
                   % (wname,ename))
            ef=open_ex(ename, 'a+')
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
        archfile=open_ex(wname,'r')
        self.processUnixMailbox(archfile, Article)
        archfile.close()
        os.unlink(wname)
        self.DropArchLock()

    def get_filename(self, article):
	return '%06i.html' % (article.sequence,)

    def get_archives(self, article):
	"""Return a list of indexes where the article should be filed.
	A string can be returned if the list only contains one entry, 
	and the empty list is legal."""
	if article.subject in ['subscribe', 'unsubscribe']: return None
        res = self.dateToVolName(string.atof(article.date))
        self.message("figuring article archives\n")
        self.message(res + "\n")
        return res

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
        volname=string.strip(volname)
        volre= { 'year' : r'^(?P<year>[0-9]{4,4})$',
                 'quarter' : r'^(?P<year>[0-9]{4,4})q(?P<quarter>[1234])$',
                 'month' : r'^(?P<year>[0-9]{4,4})-(?P<month>[a-zA-Z]+)$',
		 'week': r'^Week-of-Mon-(?P<year>[0-9]{4,4})(?P<month>[01][0-9])(?P<day>[0123][0-9])',
		 'day': r'^(?P<year>[0-9]{4,4})(?P<month>[01][0-9])(?P<day>[0123][0-9])$'}
        for each in volre.keys():
            match=re.match(volre[each],volname)
            if match:
                year=string.atoi(match.group('year'))
                month=1
		day = 1
                if each == 'quarter':
                    q=string.atoi(match.group('quarter'))
                    month=(q*3)-2
                elif each == 'month':
                    monthstr=string.lower(match.group('month'))
                    m=[]
                    for i in range(1,13):
                        m.append(string.lower(
                                 time.strftime("%B",(1999,i,1,0,0,0,0,1,0))))
                    try:
                        month=m.index(monthstr)+1
                    except ValueError:
                        pass
		elif each == 'week' or each == 'day':
		    month = string.atoi(match.group("month"))
		    day = string.atoi(match.group("day"))
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
            if msg[-1:]!='\n': f.write('\n')
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
	    self.message("Computing threaded index\n")
	    self.updateThreadedIndex()

    def write_index_footer(self):
	for i in range(self.depth): print '</UL>'
        print self.html_foot()

    def write_index_entry(self, article):
        if article.charset == self.charset:
            d = article.decoded
            subject = d.get("subject", article.subject)
            author = d.get("author", article.author)
        else:
            subject = CGIescape(article.subject)
            author = CGIescape(article.author)
        print index_entry_template % (urllib.quote(article.filename),
                                      subject, article.sequence, author)

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
        # XXX why + 910 below ???
##	print ('<LI> <A HREF="%s">%s</A> <A NAME="%i"></A><I>%s</I>'
##               % (CGIescape(urllib.quote(article.filename)),
##                  CGIescape(article.subject), article.sequence+910, 
##                  CGIescape(article.author)))

    def write_TOC(self):
        self.sortarchives()
        toc=open_ex(os.path.join(self.basedir, 'index.html'), 'w')
        toc.write(self.html_TOC())
        toc.close()

    def write_article(self, index, article, path):
        f = open_ex(path, 'w')
        f.write(article.as_html())
        f.close()

        # Write the text article to the text archive.
        path = os.path.join(self.basedir, "%s.txt" % index)
        f =open_ex(path, 'a+')
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
                archt = open_ex(txtfile, 'r')
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
                    or string.upper(each) == each):
                d[each] = self.__dict__[each]
        return d

    # Add <A HREF="..."> tags around URLs and e-mail addresses.

    def __processbody_URLquote(self, source, dest):
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

    # Escape all special characters
    def __processbody_CGIescape(self, source, dest):
        for i in xrange(0, len(source)):
	    if source[i]!=None: 
	        dest[i]=cgi.escape(source[i]) ; source[i]=None
		
    # Perform Hypermail-style processing of <HTML></HTML> directives
    # in message bodies.  Lines between <HTML> and </HTML> will be written
    # out precisely as they are; other lines will be passed to func2
    # for further processing .

    def __processbody_HTML(self, source, dest):
        l=len(source) ; i=0
	while i<l:
	    while i<l and htmlpat.match(source[i])==None: i=i+1
	    if i<l: source[i]=None ; i=i+1
	    while i<l and nohtmlpat.match(source[i])==None:
	        dest[i], source[i] = source[i], None
	        i=i+1
	    if i<l: source[i]=None ; i=i+1
	    
    def format_article(self, article):
	source=article.body ; dest=[None]*len(source)
	# Handle <HTML> </HTML> directives
	if self.ALLOWHTML: 
	    self.__processbody_HTML(source, dest)
	self.__processbody_URLquote(source, dest)
	if not self.SHOWHTML: 
	    # Do simple formatting here: <PRE>..</PRE>
	    for i in range(0, len(source)):
		s=source[i]
		if s==None: continue
		dest[i]=CGIescape(s) ; source[i]=None
	    if len(dest) > 0:
                dest.insert(0, '<PRE>')
                dest.append('</pre>')
	else:
	    # Do fancy formatting here
	    if self.SHOWBR:
		# Add <BR> onto every line
		for i in range(0, len(source)):
		    s=source[i]
		    if s==None: continue
		    s=CGIescape(s) +'<BR>'
		    dest[i]=s ; source[i]=None
	    else:
		for i in range(0, len(source)):
		    s=source[i]
		    if s==None: continue
		    s=CGIescape(s)
		    if s[0:1] in ' \t\n': s='<P>'+s
		    dest[i]=s ; source[i]=None
        article.body=filter(lambda x: x!=None, dest)
	return article

    def update_article(self, arcdir, article, prev, next):
	self.message('Updating HTML for article ' + str(article.sequence))
	try:
	    f = open_ex(os.path.join(arcdir, article.filename), 'r')
            article.loadbody_fromHTML(f)
	    f.close()
        except IOError:
            self.message("article file %s is missing!"
                         % os.path.join(arcdir, article.filename))
        article.prev = prev
        article.next = next
	f = open_ex(os.path.join(arcdir, article.filename), 'w')
	f.write(article.as_html())
	f.close()
