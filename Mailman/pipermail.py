#!/usr/local/bin/python
# Hey Emacs, this is -*-Python-*- code!
#
# Pipermail 0.0.2-mm
#
# **NOTE**
#
# This internal version of pipermail has been deprecated in favor of use of 
# an external version of pipermail, available from:
# http://starship.skyport.net/crew/amk/maintained/pipermail.html
# The external version should be pointed at the created archive files.
#
#
# Some minor mods have been made for use with the Mailman mailing list manager.
# All changes will have JV by them.
#
# (C) Copyright 1996, A.M. Kuchling (amk@magnet.com)
# Home page at http://amarok.magnet.com/python/pipermail.html
#
# HTML code for frames courtesy of Scott Hassan (hassan@cs.stanford.edu)
#
# TODO:
#  * Prev. article, next. article pointers in each article
#  * I suspect there may be problems with rfc822.py's getdate() method; 
#    take a look at the threads "Greenaway and the net (fwd)" or
#    "Pillow Book pictures".  To be looked into...
#  * Anything else Hypermail can do that we can't?
#  * General code cleanups
#  * Profiling & optimization
#  * Should there be an option to enable/disable frames?
#  * Like any truly useful program, Pipermail should have an ILU interface.
#  * There's now an option to keep from preserving line breaks, 
#    so paragraphs in messages would be reflowed by the browser.
#    Unfortunately, this mangles .sigs horribly, and pipermail doesn't yet
#    put in paragraph breaks.  Putting in the breaks will only require a
#    half hour or so; I have no clue as to how to preserve .sigs.
#  * Outside URLs shouldn't appear in the display frame.  How to fix? 
#

VERSION = "0.0.2.mm"

import posixpath, time, os, string, sys, rfc822

# JV -- to get HOME_PAGE
import mm_cfg

class ListDict:
    def __init__(self): self.dict={}
    def keys(self): return self.dict.keys()
    def __setitem__(self, key, value):
	"Add the value to a list for the key, creating the list if needed."
	if not self.dict.has_key(key): self.dict[key]=[value]
	else: self.dict[key].append(value)
    def __getitem__(self, key):
	"Return the list matching a key"
	return self.dict[key]
    
def PrintUsage():
    print """Pipermail %s
usage: pipermail [options]
options: -a URL    : URL to other archives
         -b URL    : URL to archive information
         -c file   : name of configuration file (default: ~/.pmrc)
         -d dir    : directory where the output files will be placed 
                     (default: archive/)
         -l name   : name of the output archive
         -m file   : name of input file
         -s file   : name where the archive state is stored 
                     (default: <input file>+'.pipermail'
         -u        : Select 'update' mode
         -v        : verbose mode of operation
    """ % (VERSION,)
    sys.exit(0)

# Compile various important regexp patterns
import regex, regsub
# Starting <html> directive
htmlpat=regex.compile('^[ \t]*<html>[ \t]*$')    
# Ending </html> directive
nohtmlpat=regex.compile('^[ \t]*</html>[ \t]*$') 
# Match quoted text
quotedpat=regex.compile('^[>|:]+')
# Parenthesized human name 
paren_name_pat=regex.compile('.*\([(].*[)]\).*') 
# Subject lines preceded with 'Re:' 
REpat=regex.compile('[ \t]*[Rr][Ee][ \t]*:[ \t]*')
# Lines in the configuration file: set pm_XXX = <something>
cfg_line_pat=regex.compile('^[ \t]*[sS][eE][tT][ \t]*[Pp][Mm]_\([a-zA-Z0-9]*\)'
			   '[ \t]*=[ \t]*\(.*\)[ \t\n]*$')
# E-mail addresses and URLs in text
emailpat=regex.compile('\([-+,.a-zA-Z0-9]*@[-+.a-zA-Z0-9]*\)') 
urlpat=regex.compile('\([a-zA-Z0-9]+://[^ \t\n]+\)') # URLs in text
# Blank lines
blankpat=regex.compile('^[ \t\n]*$')

def ReadCfgFile(prefs):
    import posixpath
    try:
	f=open(posixpath.expanduser(prefs['CONFIGFILE']), 'r')
    except IOError, (num, msg):
	if num==2: return
	else: raise IOError, (num, msg)
    line=0
    while(1):
	L=f.readline() ; line=line+1
	if L=="": break
	if string.strip(L)=="": continue   # Skip blank lines
	match=cfg_line_pat.match(L)
	if match==-1:
	    print "Syntax error in line %i of %s" %(line, prefs['CONFIGFILE'])
	    print L
	else:
	    varname, value=cfg_line_pat.group(1,2)
	    varname=string.upper(varname)
	    if not prefs.has_key(varname):
		print ("Unknown variable name %s in line %i of %s"
		       %(varname, line, prefs['CONFIGFILE']))
		print L
	    else:
		prefs[varname]=eval(value)
    f.close()

def ReadEnvironment(prefs):
    import sys, os
    for key in prefs.keys():
	envvar=string.upper('PM_'+key)
	if os.environ.has_key(envvar):
	    if type(prefs[key])==type(''): prefs[key]=os.environ[envvar]
	    else: prefs[key]=string.atoi(os.environ[envvar])
	    
def UpdateMsgHeaders(prefs, filename, L):
    """Update the next/previous message information in a message header.
The message is scanned for <!--next--> and <!--endnext--> comments, and
new pointers are written.  Otherwise, the text is simply copied without any processing."""
    pass
    
def ProcessMsgBody(prefs, msg, filename, articles):
    """Transform one mail message from plain text to HTML.
This involves writing an HTML header, scanning through the text looking
for <html></html> directives, e-mail addresses, and URLs, and
finishing off with a footer."""
    import cgi, posixpath
    outputname=posixpath.join(prefs['DIR'], filename)
    output=open(outputname, 'w')
    os.chmod(outputname, prefs['FILEMODE'])
    subject, email, poster, date, datestr, parent, id = articles[filename]
    # JV
    if not email:
	email = ''
    if not subject:
	subject = '<No subject>'
    if not poster:
	poster = '*Unknown*'
    if not datestr:
	datestr = ''
    output.write('<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 3.0//EN">'
                 "<html><head><title>%s Mailing List: %s</title></head>"
                 "<body><h1>%s</h1>"
                 "%s (<i>%s</i>)<br><i>%s</i><p>" %
		 (prefs['LABEL'], cgi.escape(subject),cgi.escape(subject),
		  cgi.escape(poster),cgi.escape(email),
		  cgi.escape(datestr)))
    output.write('<ul><li> <b>Messages sorted by:</b>'
	    '<a target="toc" href="date.html#1">[ date ]</a>'
	    '<a target="toc" href="thread.html#1">[ thread ]</a>'
	    '<a target="toc" href="subject.html#1">[ subject ]</a>'
	    '<a target="toc" href="author.html#1">[ author ]</a></ul>\n')
	    
    html_mode=0
    if prefs['SHOWHR']: output.write('<hr>')
    output.write('<p>')
    if not prefs['SHOWHTML']: output.write('<pre>\n')
    msg.rewindbody()			# Seek to start of message body
    quoted=-1
    while (1):
	L=msg.fp.readline()
	if L=="": break
	if html_mode:
	    # If in HTML mode, check for ending tag; otherwise, we
	    # copy the line without any changes.
	    if nohtmlpat.match(L)==-1:
		output.write(L) ; continue
	    else:
		html_mode=0
		if not prefs['SHOWHTML']: output.write('<pre>\n')
		continue
	# Check for opening <html> tag
	elif htmlpat.match(L)!=-1:
	    html_mode=1
	    if not prefs['SHOWHTML']: output.write('</pre>\n')
	    continue
	if prefs['SHOWHTML'] and prefs['IQUOTES']:
	    # Check for a line of quoted text and italicise it
	    # (We have to do this before escaping HTML special
	    # characters because '>' is commonly used.) 
	    quoted=quotedpat.match(L)
	    if quoted!=-1:
		L=cgi.escape(L[:quoted]) + '<i>' + cgi.escape(L[quoted:]) + '</i>'
		# If we're flowing the message text together, quoted lines
		# need explicit breaks, no matter what mode we're in.
		if prefs['SHOWHTML']: L=L+'<br>'
	    else: L=cgi.escape(L)
	else: L=cgi.escape(L)
	
	# Check for an e-mail address
	L2="" ; i=emailpat.search(L)
	while i!=-1:
	    length=len(emailpat.group(1))
	    mailcmd=prefs['MAILCOMMAND'] % {'TO':L[i:i+length]}
	    L2=L2+'%s<A HREF="%s">%s</A>' % (L[:i],
		 mailcmd, L[i:i+length])
	    L=L[i+length:] 
	    i=emailpat.search(L)
	L=L2+L ; L2=""; i=urlpat.search(L)
	while i!=-1:
	    length=len(urlpat.group(1))
	    L2=L2+'%s<A HREF="%s">%s</A>' % (L[:i],
		 L[i:i+length], L[i:i+length])
	    L=L[i+length:]
	    i=urlpat.search(L)
	L=L2+L
	if prefs['SHOWHTML']:
	    while (L!="" and L[-1] in '\015\012'): L=L[:-1]
	    if prefs['SHOWBR']:
		# We don't want to flow quoted passages
		if quoted==-1: L=L+'<br>'
	    else:
		# If we're not adding <br> to each line, we'll need to
		# insert <p> markup on blank lines to separate paragraphs.
		if blankpat.match(L)!=-1: L=L+'<p>'
	    L=L+'\n'
	output.write(L)
	
    if not prefs['SHOWHTML'] and not html_mode: output.write('</pre>')
    if prefs['SHOWHR']: output.write('<hr>')
    output.write('<!--next-->\n<!--endnext-->\n</body></html>')
    output.close()

def WriteHTMLIndex(prefs, fp, L, articles, indexname):
    """Process a list L into an HTML index, written to fp.
L is processed from left to right, and contains a list of 2-tuples;
an integer of 1 or more giving the depth of indentation, and
a list of strings which are used to reference the 'articles'
dictionary.  Most of the time the lists contain only 1 element."""
    fp.write('<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 3.0//EN">\n'
            "<html><head><base target=display>"
	    "<title>%s Mailing List Archive by %s</title></head><body>\n"
	    % (prefs['LABEL'], indexname))
    fp.write('<H1><A name="start">%s Mailing List Archive by %s</A></H1>'
            '<ul><li> <b><a target="toc" href="#end">Most recent messages</a></b>'
	    '<li> <b>Messages sorted by:</b>'
	    % (prefs['LABEL'], indexname))
    if indexname!='Date':
	fp.write('<a target="toc" href="date.html#start">[ date ]</a>')
    if indexname!='Subject':
	fp.write('<a target="toc" href="subject.html#start">[ subject ]</a>')
    if indexname!='Author':
	fp.write('<a target="toc" href="author.html#start">[ author ]</a>')
    if indexname!='Thread':
	fp.write('<a target="toc" href="thread.html#start">[ thread ]</a>')
    if prefs['ARCHIVES']!='NONE':
	fp.write('<li> <b><a href="%s">Other mail archives</a></b>' %
		(prefs['ARCHIVES'],))
# This doesn't look professional.  -- JV
#    mailcmd=prefs['MAILCOMMAND'] % {'TO':'amk@magnet.com'}
#    fp.write('</ul><p>Please inform <A HREF="%s">amk@magnet.com</a> if any of the messages are formatted incorrectly.' % (mailcmd,) ) 
    
    fp.write("<p><b>Starting:</b> <i>%s</i><br>"
	     "<b>Ending:</b> <i>%s</i><br><b>Messages:</b> %i<p>"
	     % (prefs['firstDate'], prefs['endDate'], len(L)) )

    # Write the index
    level=1
    fp.write('<ul>\n')
    for indent, keys in L:
	if indent>level and indent<=prefs['THRDLEVELS']:
	    fp.write((indent-level)*'<ul>'+'\n')
	if indent<level: fp.write((level-indent)*'</ul>'+'\n')
	level=indent
	for j in keys:
	    subj, email, poster, date, datestr, parent, id=articles[j]
	    # XXX Should we put a mailto URL in here?
	    fp.write('<li> <A HREF="%s"><b>%s</b></a> <i>%s</i>\n' %
		     (j, subj, poster) )
    for i in range(0, indent): fp.write('</ul>')
    fp.write('<p>')

    # Write the footer
    import time
    now=time.asctime(time.localtime(time.time()))
    
# JV -- Fixed a bug here.
    if prefs['ARCHIVES'] <> 'NONE':
	otherstr=('<li> <b><a href="%s">Other mail archives</a></b>' %
		  (prefs['ARCHIVES'],) )
    else: otherstr=""
    fp.write('<a name="end"><b>Last message date:</b></a> <i>%s</i><br>'
	    '<b>Archived on:</b> <i>%s</i><p><ul>'
	    '<li> <b>Messages sorted by:</b>'
	    '<a target="toc" href="date.html#start">[ date ]</a>'
	    '<a target="toc" href="subject.html#start">[ subject ]</a>'
	    '<a target="toc" href="author.html#start">[ author ]</a>'
	    '<a target="toc" href="thread.html#start">[ thread ]</a>'
	    '%s</ul><p>' % (prefs['endDate'], now, otherstr))
	    
    fp.write('<p><hr><i>This archive was generated by '
# JV Updated the URL.
	     '<A HREF="http://www.magnet.com/~amk/python/pipermail.html">'
	     'Pipermail %s</A>.</i></body></html>' % (VERSION,))

# Set the hard-wired preferences first
# JV Changed the SHOWHTML pref default to 0 because 1 looks bad.
prefs={'CONFIGFILE':'~/.pmrc', 'MBOX':'mbox',
	     'ARCHIVES': 'NONE', 'ABOUT':'NONE', 'REVERSE':0,
	     'SHOWHEADERS':0, 'SHOWHTML':0, 'LABEL':"",
	     'DIR':'archive', 'DIRMODE':0755,
	     'FILEMODE':0644, 'OVERWRITE':0, 'VERBOSE':0,
	     'THRDLEVELS':3, 'SHOWBR':0, 'IQUOTES':1,
	     'SHOWHR':1, 'MAILCOMMAND':'mailto:%(TO)s',
	     'INDEXFILE':'NONE'
}

# Read the ~/.pmrc file
ReadCfgFile(prefs)
# Read environment variables
ReadEnvironment(prefs)

# Parse command-line options
import getopt
options, params=getopt.getopt(sys.argv[1:], 'a:b:c:d:l:m:s:uipvxzh?')
for option, value in options:
    if option=='-a': prefs['ARCHIVES']=value
    if option=='-b': prefs['ABOUT']=value
    if option=='-c': prefs['CONFIGFILE']=value
    if option=='-d': prefs['DIR']=value
#    if option=='-f': prefs.frames=1 
    if option=='-i': prefs['MBOX']='-'
    if option=='-l': prefs['LABEL']=value
    if option=='-m': prefs['MBOX']=value
    if option=='-s': prefs['INDEXFILE']=value
    if option=='-p' or option=='-v': prefs['VERBOSE']=1
    if option=='-x': prefs['OVERWRITE']=1
    if option=='-z' or option=='-h' or option=='-?': PrintUsage()

# Set up various variables
articles={} ; sequence=0
for key in ['INDEXFILE', 'MBOX', 'CONFIGFILE', 'DIR']:
    prefs[key]=posixpath.expanduser(prefs[key])
      
if prefs['INDEXFILE']=='NONE':
    if prefs['MBOX']!='-':
	prefs['INDEXFILE']=prefs['MBOX']+'.pipermail'
    else: prefs['INDEXFILE']='mbox.pipermail'

# Read an index file, if one can be found
if not prefs['OVERWRITE']:
    # Look for a file contained pickled state
    import pickle
    try:
	if prefs['VERBOSE']:
	    print 'Attempting to read index file', prefs['INDEXFILE']
	f=open(prefs['INDEXFILE'], 'r')
	articles, sequence =pickle.load(f)
	f.close()
    except IOError:
	if prefs['VERBOSE']: print 'No index file found.'	
	pass		# Ignore errors

# Open the input file 
if prefs['MBOX']=='-': prefs['MBOX']=sys.stdin
else:
    if prefs['VERBOSE']: print 'Opening input file', prefs['MBOX']
    prefs['MBOX']=open(prefs['MBOX'], 'r')

# Create the destination directory; if it already exists, we don't care
try:
    os.mkdir(prefs['DIR'], prefs['DIRMODE'])
    if prefs['VERBOSE']: print 'Directory %s created'%(prefs['DIR'],)
except os.error, (errno, errmsg): pass

# Create various data structures:
# msgids maps Message-IDs to filenames.
# roots maps Subject lines to (date, filename) tuples, and is used to
# identify the oldest article with a given subject line for threading.

msgids={} ; roots={}
for i in articles.keys():
    subject, email, poster, date, datestr, parent, id =articles[i]
    if id: msgids[id]=i
    if not roots.has_key(subject) or roots[subject]<date:
	roots[subject]=(date, i)

# Start processing the index
import mailbox
mbox=mailbox.UnixMailbox(prefs['MBOX'])
while (1):
    m=mbox.next()
    if not m: break

    filename='%04i.html' % (sequence,)
    if prefs['VERBOSE']: sys.stdout.write("Processing "+filename+"\n")
    # The apparently redundant str() actually catches the case where
    # m.getheader() returns None.
    subj=str(m.getheader('Subject'))
    # Remove any number of 'Re:' prefixes from the subject line
    while (1):
	i=REpat.match(subj)
	if i!=-1: subj=subj[i:]
	else: break
    # Locate an e-mail address
    L=m.getheader('From')
    # JV: sometimes there is no From header, so use the one from unixfrom.
    if not L:
	try:
	    L = string.split(m.unixfrom)[1]
	except:
	    L = "***Unknown***"
    email=None
    i=emailpat.search(L)
    if i!=-1:
	length=emailpat.match(L[i:])
	email=L[i:i+length]
    # Remove e-mail addresses inside angle brackets
    poster=str(regsub.gsub('<.*>', '', L))
    # Check if there's a name in parentheses
    i=paren_name_pat.match(poster)
    if i!=-1: poster=paren_name_pat.group(1)[1:-1]
    datestr=m.getheader('Date')
    # JV -- Hacks to make the getdate work.
    # These hacks might skew the post time a bit.
    # Crude, but so far, effective.
    words = string.split(datestr)
    if ((len(words[-1]) == 4) and (len(words) == 5) 
	and (words[-1][:-1] == '199')):
        try:
	  date = time.mktime(rfc822.parsedate('%s, %s %s %s %s' %
					    (words[0], words[2], words[1],
					     words[4], words[3])))
	except:
	    date = time.mktime(m.getdate('Date')) # Odd
    elif len(words) > 4 and words[4][-1] == ',':
	try:
	    date = time.mktime(rfc822.parsedate('%s, %s %s %s %s' %
					    (words[0], words[1], words[2], 
					     words[3], words[4][:-1])))
	except:
	    date = time.mktime(m.getdate('Date')) # Hmm
    else:
	try:
	    date=time.mktime(m.getdate('Date'))
	except:
	    print 'Error getting date!'
	    print 'Subject = ', m.getheader('subject')
	    print 'Date = ', m.getheader('date')
	    
    id=m.getheader('Message-Id')
    if id: id=id[1:-1] ; msgids[id]=filename
    parent=None
    in_reply_to=m.getheader('In-Reply-To')
    if in_reply_to:
	in_reply_to=in_reply_to[1:-1]
    if msgids.has_key(in_reply_to): parent=msgids[in_reply_to]
    elif roots.has_key(subj) and roots[subj][0]<date:
	parent=roots[subj][1]
    else: roots[subj]=(date,filename)
	
    articles[filename]=(subj, email, poster, date, datestr, parent, id)
    ProcessMsgBody(prefs, m, filename, articles)
    sequence=sequence+1
prefs['MBOX'].close()

if prefs['VERBOSE']: sys.stdout.write("Writing date index\n")
import time
indexname=posixpath.join(prefs['DIR'], 'date.html')
f=open(indexname, 'w') ; os.chmod(indexname, prefs['FILEMODE'])
dates=ListDict()
for i in articles.keys():
    subject, email, poster, date, datestr, parent, id=articles[i] 
    dates[date]=i
L=dates.keys() ; L.sort()
if prefs['REVERSE']: L.reverse()
prefs['firstDate']=time.asctime(time.localtime(L[0]))
prefs['endDate']=time.asctime(time.localtime(L[-1]))
L=map(lambda key, s=dates: (1,s[key]), L)
WriteHTMLIndex(prefs, f, L, articles, 'Date')
f.close() ; del dates, L

if prefs['VERBOSE']: sys.stdout.write("Writing thread index\n")
indexname=posixpath.join(prefs['DIR'], 'thread.html')
f=open(indexname, 'w') ; os.chmod(indexname, prefs['FILEMODE'])
def DFS(p, N=None, depth=0, prefs=prefs):
    set=filter(lambda x, N=N, p=p: p[x][1]==N, p.keys())
    set=map(lambda x, a=articles: (articles[x][3],x), set)
    set.sort()
    if prefs['REVERSE']: set.reverse()
    set=map(lambda x: x[1], set)
    if len(set)==0: return [(depth, [N])]
    else:
	L=[]
	for i in set:
	    L=L+DFS(p, i, depth+1)
	return [(depth,[N])]+L
parents={}
for i in articles.keys():
    subject, email, poster, date, datestr, parent, id=articles[i]
    parents[i]=(date, parent)
L=DFS(parents)[1:]
WriteHTMLIndex(prefs, f, L, articles, 'Thread')
f.close() ; del L, parents

if prefs['VERBOSE']: sys.stdout.write("Writing subject index\n")
indexname=posixpath.join(prefs['DIR'], 'subject.html')
f=open(indexname, 'w') ; os.chmod(indexname, prefs['FILEMODE'])
subjects=ListDict()
for i in articles.keys():
    subject, email, poster, date, datestr, parent, id=articles[i] 
    subjects[(subject, date)]=i
L=subjects.keys() ; L.sort() ; L=map(lambda key, s=subjects: (1, s[key]), L)
WriteHTMLIndex(prefs, f, L, articles, 'Subject')
f.close() ; del subjects, L

if prefs['VERBOSE']: sys.stdout.write("Writing author index\n")
indexname=posixpath.join(prefs['DIR'], 'author.html')
f=open(indexname, 'w') ; os.chmod(indexname, prefs['FILEMODE'])
authors=ListDict()
for i in articles.keys():
    v=articles[i]
    authors[(v[2],v[3])]=i
L=authors.keys() ; L.sort() ; L=map(lambda key, s=authors: (1,s[key]), L)
WriteHTMLIndex(prefs, f, L, articles, 'Author')
f.close() ; del authors, L

if prefs['VERBOSE']: sys.stdout.write("Writing framed index\n")
f=open(posixpath.join(prefs['DIR'], 'blank.html'), 'w')
f.write("<html></html>") ; f.close()
# JV changed...
f=open(posixpath.join(prefs['DIR'], mm_cfg.HOME_PAGE), 'w')
f.write("""<html><head><title>%s Pipermail Archive</title>
<frameset cols="*, 60%%">
<FRAME SRC="thread.html" NAME=toc>
<FRAME SRC="blank.html" NAME=display>
</frameset></head>
<body><noframes>
To access the %s Pipermail Archive, choose one of the following links:
<p>
Messages sorted by <a target="toc" href="date.html#start">[ date ] </a>
<a target="toc" href="subject.html#start">[ subject ]</a>
<a target="toc" href="author.html#start">[ author ]</a>
<a target="toc" href="thread.html#start">[ thread ]</a>
</ol>
</noframes>
</body></html>
""" % (prefs['LABEL'],prefs['LABEL']) )


import pickle
if prefs['VERBOSE']: print 'Writing index file', prefs['INDEXFILE']
f=open(prefs['INDEXFILE'], 'w')
pickle.dump( (articles, sequence), f )
f.close()
