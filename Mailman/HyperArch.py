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

import re, cgi, urllib, string
import time, pickle, os, posixfile
import HyperDatabase
import pipermail
import mm_cfg


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
From %(email)s %(datestr)s
Date: %(datestr)s
From: %(author)s %(email)s
Subject: %(subject)s

%(body)s

"""

article_template="""\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
 <HEAD>
   <TITLE> %(subject_html)s</TITLE>
   <LINK REL="Index" HREF="index.html" >
   <LINK REL="made" HREF="mailto:%(email_url)s">
   %(prev)s
   %(next)s
 </HEAD>
 <BODY BGCOLOR="#ffffff">
   <H1>%(subject_html)s</H1>
    <B>%(author_html)s</B> 
    <A HREF="mailto:%(email_url)s" TITLE="%(subject_html)s">%(email_html)s</A><BR>
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
"""



def CGIescape(arg): 
    s=cgi.escape(str(arg))
    s=re.sub('"', '&quot;', s)
    return s

# Parenthesized human name 
paren_name_pat=re.compile(r'([(].*[)])') 
# Subject lines preceded with 'Re:' 
REpat=re.compile( r"\s*RE\s*:\s*",
		  re.IGNORECASE)
# E-mail addresses and URLs in text
emailpat=re.compile(r'([-+,.\w]+@[-+.\w]+)') 
#  Argh!  This pattern is buggy, and will choke on URLs with GET parameters.
urlpat=re.compile(r'(\w+://[^>)\s]+)') # URLs in text
# Blank lines
blankpat=re.compile(r'^\s*$')

# 
# Starting <html> directive
htmlpat=re.compile(r'^\s*<HTML>\s*$', re.IGNORECASE)    
# Ending </html> directive
nohtmlpat=re.compile(r'^\s*</HTML>\s*$', re.IGNORECASE) 
# Match quoted text
quotedpat=re.compile(r'^([>|:]|&gt;)+')


# Note: I'm overriding most, if not all of the pipermail Article class here -ddm
# The Article class encapsulates a single posting.  The attributes 
# are:
#
#  sequence : Sequence number, unique for each article in a set of archives
#  subject  : Subject
#  datestr  : The posting date, in human-readable format
#  date     : The posting date, in purely numeric format
#  headers  : Any other headers of interest
#  author   : The author's name (and possibly organization)
#  email    : The author's e-mail address
#  msgid    : A unique message ID
#  in_reply_to : If !="", this is the msgid of the article being replied to
#  references: A (possibly empty) list of msgid's of earlier articles in the thread
#  body     : A list of strings making up the message body

class Article(pipermail.Article):
    __last_article_time=time.time()

    html_tmpl=article_template
    text_tmpl=article_text_template


    def as_html(self):
	d = self.__dict__.copy()
	if self.prev:
	    d["prev"] = '<LINK REL="Previous"  HREF="%s">' % \
			(url_quote(self.prev.filename))
	    d["prev_wsubj"] = '<LI> Previous message: <A HREF="%s">%s</A></li>' % \
			      (url_quote(self.prev.filename), html_quote(self.prev.subject))
	else:
	    d["prev"] = d["prev_wsubj"] = ""
	    
	if self.next:
	    d["next"] = '<LINK REL="Next" HREF="%s">' % \
			(html_quote(self.next.filename))
	    d["next_wsubj"] = '<LI> Next message: <A HREF="%s">%s</A></li>' % \
			      (url_quote(self.next.filename), html_quote(self.next.subject))	    
	else:
	    d["next"] = d["next_wsubj"] = ""
	
	d["email_html"] = html_quote(self.email)
	d["subject_html"] = html_quote(self.subject)
	d["author_html"] = html_quote(self.author)
	d["email_url"] = url_quote(self.email)
	d["datestr_html"] = html_quote(self.datestr)
	d["body"] = string.join(self.body, "")
        return self.html_tmpl % d

    def as_text(self):
	d = self.__dict__.copy()
	d["body"] = string.join(self.body, "")
        return self.text_tmpl % d


    def __init__(self, message=None, sequence=0, keepHeaders=[]):
	import time
	if message==None: return
	self.sequence=sequence

	self.parentID = None 
        self.threadKey = None
        self.prev=None
        self.next=None
	# otherwise the current sequence number is used.
	id=pipermail.strip_separators(message.getheader('Message-Id'))
	if id=="": self.msgid=str(self.sequence)
	else: self.msgid=id

	if message.has_key('Subject'): self.subject=str(message['Subject'])
	else: self.subject='No subject'
	i=0
	while (i!=-1):
	    result=REpat.match(self.subject)
	    if result: 
		i = result.end(0)
		self.subject=self.subject[i:]
	    else: i=-1
	if self.subject=="": self.subject='No subject'

	if message.has_key('Date'): 
	    self.datestr=str(message['Date'])
   	    date=message.getdate_tz('Date')
	else: 
	    self.datestr='None' 
	    date=None
	if date!=None:
	    date, tzoffset=date[:9], date[-1] 
            if not tzoffset:
                tzoffset = 0
	    date=time.mktime(date)-tzoffset
	else:
	    date=self.__last_article_time+1 
	    
	self.__last_article_time=date 
	self.date='%011i' % (date,)

	# Figure out the e-mail address and poster's name
	self.author, self.email=message.getaddr('From')
	self.email=pipermail.strip_separators(self.email)
	self.author=pipermail.strip_separators(self.author)

	if self.author=="": self.author=self.email

	# Save the 'In-Reply-To:' and 'References:' lines
	i_r_t=message.getheader('In-Reply-To')
	if i_r_t==None: self.in_reply_to=''
	else:
	    match=pipermail.msgid_pat.search(i_r_t)
	    if match==None: self.in_reply_to=''
	    else: self.in_reply_to=pipermail.strip_separators(match.group(1))
		
	references=message.getheader('References')
	if references==None: self.references=[]
	else: self.references=map(pipermail.strip_separators, string.split(references))

	# Save any other interesting headers
	self.headers={}
	for i in keepHeaders:
	    if message.has_key(i): self.headers[i]=message[i]

	# Read the message body
	self.body=[]
	message.rewindbody()
	while (1):
	    line=message.fp.readline()
	    if line=="": break
	    self.body.append(line)
	
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
index_header_template="""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
  <HEAD>
     <title>The %(listname)s %(archive)s Archive by %(archtype)s</title>
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

	     <li><b><a href="%(listinfo)s">More info on this list...</a></b></li>
      </ul>
      <p><b>Starting:</b> <i>%(firstdate)s</i><br>
         <b>Ending:</b> <i>%(lastdate)s</i><br>
         <b>Messages:</b> %(size)s<p>
     <ul>
"""

index_footer_template="""\
    </ul>
    <p>
      <a name="end"><b>Last message date:</b></a> 
       <i>%(lastdate)s</i><br>
    <b>Archived on:</b> <i><!--#var archivedate --></i>
    <p>
   <ul>
         <li> <b>Messages sorted by:</b>
	        %(thread_ref)s
		%(subject_ref)s
		%(author_ref)s
		%(date_ref)s
	     <li><b><a href="%(listinfo)s">More info on this list...</a></b></li>
     </ul>
     <p>
     <hr>
     <i>This archive was generated by
     <a href="http://starship.skyport.net/crew/amk/maintained/pipermail.html">
     Pipermail %(version)s</a>.</i>
  </BODY>
</HTML>
"""

TOC_template="""\
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
"""

TOC_entry_template = """\

	    <tr>
            <td>%(archive)s:</td>
            <td>
              <A href="%(archive)s/thread.html">[ Thread ]</a>
              <A href="%(archive)s/subject.html">[ Subject ]</a>
              <A href="%(archive)s/author.html">[ Author ]</a>
              <A href="%(archive)s/date.html">[ Date ]</a>
            </td>
            <td><A href="%(archive)s.txt">[ Text ]</a></td>
            </tr>

"""
arch_listing_start = """\
	<table border=3>
          <tr><td>Archive</td> <td>View by:</td> <td>Downloadable version</td></tr>
"""

arch_listing_end = """\
         </table>
"""
 

class HyperArchive(pipermail.T):

    # some defaults
    DIRMODE=0775 
    FILEMODE=0664
    

    VERBOSE=0
    DEFAULTINDEX='thread'
    ARCHIVE_PERIOD='month'
 
    THREADLAZY=0
    THREADLEVELS=3

    ALLOWHTML=1
    SHOWHTML=1
    IQUOTES=1
    SHOWBR=1

    html_hdr_tmpl=index_header_template
    html_foot_tmpl=index_footer_template
    html_TOC_tmpl=TOC_template
    TOC_entry_tmpl = TOC_entry_template    
    arch_listing_start = arch_listing_start
    arch_listing_end = arch_listing_end

    def html_foot(self):
	d = {"lastdate": html_quote(self.lastdate),
	     "archivedate": html_quote(self.archivedate),
	     "listinfo": self.maillist.GetAbsoluteScriptURL('listinfo'),
	     "version": self.version}
	for t in ("thread", "subject", "author", "date"):
	    cap = string.upper(t[0]) + t[1:]
	    if self.type == cap:
		d["%s_ref" % (t)] = ""
	    else:
		d["%s_ref" % (t)] = '<a href="%s.html#start">[ %s ]</a>' % (t, t)	
        return self.html_foot_tmpl % d


    def html_head(self):
	d = {"listname": html_quote(self.maillist.real_name),
	     "archtype": self.type,
	     "archive": self.archive,
	     "listinfo": self.maillist.GetAbsoluteScriptURL('listinfo'),
	     "firstdate": html_quote(self.firstdate),
	     "lastdate": html_quote(self.lastdate),
	     "size": self.size,
	     }
	for t in ("thread", "subject", "author", "date"):
	    cap = string.upper(t[0]) + t[1:]
	    if self.type == cap:
		d["%s_ref" % (t)] = ""
	    else:
		d["%s_ref" % (t)] = '<a href="%s.html#start">[ %s ]</a>' % (t, t)
        return self.html_hdr_tmpl % d



    def html_TOC(self):
        d = {"listname": self.maillist.real_name,
             "listinfo": self.maillist.GetAbsoluteScriptURL('listinfo') }
        listing = ""
        if not self.archives:
            d["noarchive_msg"] = '<P>Currently, there are no archives. </P>'
            d["archive_listing_start"] = ""
            d["archive_listing_end"] = ""
            d["archive_listing"] = ""
        else:
            d["noarchive_msg"] = ""
            d["archive_listing_start"] = self.arch_listing_start
            d["archive_listing_end"] = self.arch_listing_end
            for a in self.archives:
                listing = listing + self.TOC_entry_tmpl % {"archive": a}
        d["archive_listing"] = listing
        return self.html_TOC_tmpl % d



    def __init__(self, maillist,unlock=1):
        self.maillist=maillist
        self._unlocklist=unlock
        self._lock_file=None
 

        #
        # this is always called from inside it's own forked
        # process, and access is protected via list.Save()
        # so we're leavin' the perms wide open from here on out
        #
        ou = os.umask(0)
        #
        # can't init the database while other
        # processes are writing to it!
        # XXX TODO- implement native locking
        # with mailman's flock module for HyperDatabase.HyperDatabase
        #
	pipermail.T.__init__(self,
			     maillist.archive_directory,
			     reload=1,
			     database=HyperDatabase.HyperDatabase(maillist.archive_directory))

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

    def GetArchLock(self):
        if self._lock_file:
            return 1
        ou = os.umask(0)
        try:
            self._lock_file = posixfile.open(
                              os.path.join(mm_cfg.LOCK_DIR, '%s@arch.lock' % 
                              self.maillist._internal_name), 'a+')
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
            wf=open(wname,'r')
            self.maillist.LogMsg("error","Archive working file %s present. "
                                 "Check %s for possibly unarchived msgs" %
                                  (wname,ename) )
            ef=open(ename, 'a+')
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
        archfile=open(wname,'r')
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
        import sys
        sys.stderr.write("figuring article archives\n")
        sys.stderr.write(res + "\n")
        return res
    


# The following two methods should be inverses of each other. -ddm

    def dateToVolName(self,date):
        datetuple=time.gmtime(date)
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
	    datetuple = list(datetuple)
	    datetuple[2] = datetuple[2] - datetuple[6] # subtract week day
	    #
	    # even if the the day of the month counter is negative,
	    # we still get the right thing from strftime! -scott
	    #
	    return time.strftime("Week-of-Mon-%Y%m%d", tuple(datetuple))
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

    def message(self, msg):
	if self.VERBOSE:
            import sys
            f = sys.stderr
            f.write(msg)
            if msg[-1:]!='\n': f.write('\n')
            f.flush()

    def open_new_archive(self, archive, archivedir):
	import os
	index_html=os.path.join(archivedir, 'index.html') 
	try: os.unlink(index_html)
	except: pass
	os.symlink(self.DEFAULTINDEX+'.html',index_html)


    def write_index_header(self):
	self.depth=0
        print self.html_head()

        if not self.THREADLAZY and self.type=='Thread':
	    # Update the threaded index
	    self.message("Computing threaded index\n")
	    self.updateThreadedIndex()


    def write_index_footer(self):
	import string
	for i in range(self.depth): print '</UL>'
        print self.html_foot()

    def write_index_entry(self, article):
	print '<LI> <A HREF="%s">%s</A> <A NAME="%i"></A><I>%s</I>' % (urllib.quote(article.filename), 
								     CGIescape(article.subject), article.sequence, 
								     CGIescape(article.author))

    def write_threadindex_entry(self, article, depth):
	if depth<0: 
	    sys.stderr.write('depth<0') ; depth=0
	if depth>self.THREADLEVELS: depth=self.THREADLEVELS
	if depth<self.depth: 
	    for i in range(self.depth-depth): print '</UL>'
	elif depth>self.depth: 
	    for i in range(depth-self.depth): print '<UL>'
	print '<!--%i %s -->' % (depth, article.threadKey)
	self.depth=depth
	print '<LI> <A HREF="%s">%s</A> <A NAME="%i"></A><I>%s</I>' % (CGIescape(urllib.quote(article.filename)),
								     CGIescape(article.subject), article.sequence+910, 
								     CGIescape(article.author))

    def write_TOC(self):
        self.sortarchives()
        toc=open(os.path.join(self.basedir, 'index.html'), 'w')
        toc.write(self.html_TOC())
        toc.close()


    # Archive an Article object.
    def add_article(self, article):
        # Determine into what archives the article should be placed
        archives=self.get_archives(article)
        if archives==None: archives=[]        # If no value was returned, ignore it
        if type(archives)==type(''): archives=[archives]        # If a string was returned, convert to a list
        if archives==[]: return         # Ignore the article

        # Add the article to each archive in turn
        article.filename=filename=self.get_filename(article)
        article_text=article.as_text()
        temp=self.format_article(article) # Reformat the article
        self.message("Processing article #"+str(article.sequence)+' into archives '+str(archives))
        for i in archives:
            self.archive=i
            archivedir=os.path.join(self.basedir, i)
            # If it's a new archive, create it
            if i not in self.archives: 
                self.archives.append(i) ; self.update_TOC=1
                self.database.newArchive(i)
                # If the archive directory doesn't exist, create it
                try: os.stat(archivedir)
                except os.error, errdata:
                    errno, errmsg=errdata
                    if errno==2: 
                        os.mkdir(archivedir)
                    else: raise os.error, errdata
                self.open_new_archive(i, archivedir)

            # Write the HTML-ized article to the html archive.
            f=open(os.path.join(archivedir, filename), 'w')

            f.write(temp.as_html())
            f.close()

            # Write the text article to the text archive.
            archivetextfile=os.path.join(self.basedir,"%s.txt" % i)
            f=open(archivetextfile, 'a+')

            f.write(article_text)
            f.close()

            authorkey=pipermail.fixAuthor(article.author)+'\000'+article.date
            subjectkey=string.lower(article.subject)+'\000'+article.date

            # Update parenting info
            parentID=None
            if article.in_reply_to!='': parentID=article.in_reply_to
            elif article.references!=[]: 
                # Remove article IDs that aren't in the archive
                refs=filter(lambda x, self=self: self.database.hasArticle(self.archive, x), 
                            article.references)
                if len(refs):
                    refs=map(lambda x, s=self: s.database.getArticle(s.archive, x), refs)
                    maxdate=refs[0]
                    for ref in refs[1:]: 
                        if ref.date>maxdate.date: maxdate=ref
                    parentID=maxdate.msgid
            else:
                # Get the oldest article with a matching subject, and assume this is 
                # a follow-up to that article
                parentID=self.database.getOldestArticle(self.archive, article.subject)

            if parentID!=None and not self.database.hasArticle(self.archive, parentID): 
                parentID=None
            article.parentID=parentID 
            if parentID!=None:
                parent=self.database.getArticle(self.archive, parentID)
                article.threadKey=parent.threadKey+article.date+'-'
            else: article.threadKey=article.date+'-'
            self.database.setThreadKey(self.archive, article.threadKey+'\000'+article.msgid, article.msgid)
            self.database.addArticle(i, temp, subjectkey, authorkey)
            
            if i not in self._dirty_archives: 
                self._dirty_archives.append(i)
        del temp


    # Update only archives that have been marked as "changed".
    def update_dirty_archives(self):
        for i in self._dirty_archives:
            self.update_archive(i)
            archz=None
            archt=None
            try:
                import gzip
                try: 
                    archt=open(os.path.join(self.basedir,"%s.txt" % i),"r") 
                    try: 
                        os.rename(os.path.join(self.basedir,"%s.txt.gz" % i),
                              os.path.join(self.basedir,"%s.old.txt.gz" % i))
                        archz=gzip.open(os.path.join(self.basedir,"%s.old.txt.gz" % i),"r")
                    except (IOError, RuntimeError, os.error):
                        pass
                    newz=gzip.open(os.path.join(self.basedir,"%s.txt.gz" % i),"w") 
		    if archz :
                        newz.write(archz.read())
                        archz.close()
                        os.unlink(os.path.join(self.basedir,"%s.old.txt.gz" % i))
                    newz.write(archt.read())
                    newz.close()
                    archt.close()
                    os.unlink(os.path.join(self.basedir,"%s.txt" % i))
                except IOError:
                    pass
            except ImportError:
                pass
        self._dirty_archives=[]

    def close(self):
        "Close an archive, saving its state and updating any changed archives."
        self.update_dirty_archives()# Update all changed archives
        # If required, update the table of contents
        if self.update_TOC or 1:
            self.update_TOC=0
            self.write_TOC()
        # Save the collective state 
        self.message('Pickling archive state into '+os.path.join(self.basedir, 'pipermail.pck'))
        self.database.close()
        del self.database
        f=open(os.path.join(self.basedir, 'pipermail.pck'), 'w')
        pickle.dump(self.__getstate__(), f)
        f.close()

    def __getstate__(self):
        d={}
        for each in self.__dict__.keys():
            if not (each in ['maillist','_lock_file','_unlocklist']):
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
		    if self.SHOWHTML: suffix=suffix+'<BR>'
		    if not last_line_was_quoted: prefix='<BR>'+prefix
		    L= L[quoted:] 
		    last_line_was_quoted=1
	    # Check for an e-mail address
	    L2="" ; jr=emailpat.search(L) ; kr=urlpat.search(L)
	    while jr!=None or kr!=None:
		if jr==None: j=-1
		else: j = jr.start(0)
		if kr==None: k=-1
		else: k = kr.start(0)
		if j!=-1 and (j<k or k==-1): text=jr.group(1) ; URL='mailto:'+text ; pos=j
		elif k!=-1 and (j>k or j==-1): text=URL=kr.group(1) ; pos=k
		else: # j==k
		    raise ValueError, "j==k: This can't happen!"
		length=len(text)
#		sys.stderr.write("URL: %s %s %s \n" % (CGIescape(L[:pos]), URL, CGIescape(text)))
		L2=L2+'%s<A HREF="%s">%s</A>' % (CGIescape(L[:pos]), URL, CGIescape(text))
		L=L[pos+length:]
		jr=emailpat.search(L) ; kr=urlpat.search(L)
	    if jr==None and kr==None: L=CGIescape(L)
	    L=prefix+L2+L+suffix
	    if L!=Lorig: source[i], dest[i]=None, L

    # Escape all special characters
    def __processbody_CGIescape(self, source, dest):
        import cgi
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
		dest[0]='<PRE>'+dest[0] ; dest[-1]=dest[-1]+'</PRE>'
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
	import os
	self.message('Updating HTML for article '+str(article.sequence))
	try:
	    f=open(os.path.join(arcdir, article.filename), 'r')
            article.loadbody_fromHTML(f)
	    f.close()
        except IOError:
            self.message("article file %s is missing!" % os.path.join(arcdir, article.filename)) 
        article.prev=prev
        article.next=next
	f=open(os.path.join(arcdir, article.filename), 'w')
	f.write(article.as_html())
	f.close()










