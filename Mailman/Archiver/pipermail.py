#!/usr/local/bin/python

import os, sys, pickle, string, re

__version__='0.05'
VERSION=__version__
CACHESIZE=100    # Number of slots in the cache

msgid_pat=re.compile(r'(<.*>)')
def strip_separators(s):
    "Remove quotes or parenthesization from a Message-ID string"
    if s==None or s=="": return ""
    if s[0] in '"<([' and s[-1] in '">)]': s=s[1:-1]
    return s

smallNameParts = ['van', 'von', 'der', 'de']

def fixAuthor(author):
    "Canonicalize a name into Last, First format"
    # If there's a comma, guess that it's already in "Last, First" format
    if ',' in author: return author
    L=string.split(author)
    i=len(L)-1
    if i==0: return author # The string's one word--forget it
    if string.upper(author)==author or string.lower(author)==author:
	# Damn, the name is all upper- or lower-case.  
	while i>0 and string.lower(L[i-1]) in smallNameParts: i=i-1
    else:
	# Mixed case; assume that small parts of the last name will be
        # in lowercase, and check them against the list.
	while i>0 and (L[i-1][0] in string.lowercase or 
		       string.lower(L[i-1]) in smallNameParts): 
	    i=i-1
    author=string.join(L[-1:]+L[i:-1], ' ')+', '+string.join(L[:i], ' ')
    return author

# Abstract class for databases

class Database:    
    def __init__(self): pass
    def close(self): pass
    def getArticle(self, archive, msgid): pass
    def hasArticle(self, archive, msgid): pass
    def addArticle(self, archive, article, subjectkey, authorkey): pass
    def firstdate(self, archive): pass
    def lastdate(self, archive): pass
    def first(self, archive, index): pass
    def next(self, archive, index): pass
    def numArticles(self, archive): pass
    def newArchive(self, archive): pass
    def setThreadKey(self, archive, key, msgid): pass
    def getOldestArticle(self, subject): pass

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

class Article:
    import time
    __last_article_time=time.time()
    def __init__(self, message=None, sequence=0, keepHeaders=[]):
	import time
	if message==None: return
	self.sequence=sequence

	self.parentID = None ; self.threadKey = None
	# otherwise the current sequence number is used.
	id=strip_separators(message.getheader('Message-Id'))
	if id=="": self.msgid=str(self.sequence)
	else: self.msgid=id

	if message.has_key('Subject'): self.subject=str(message['Subject'])
	else: self.subject='No subject'
	if self.subject=="": self.subject='No subject'

	if message.has_key('Date'): 
	    self.datestr=str(message['Date'])
   	    date=message.getdate_tz('Date')
	else: 
	    self.datestr='None' 
	    date=None
	if date!=None:
	    date, tzoffset=date[:9], date[-1] 
	    date=time.mktime(date)-tzoffset
	else:
	    date=self.__last_article_time+1 ; print 'Article without date:', self.msgid
	    
	self.__last_article_time=date 
	self.date='%011i' % (date,)

	# Figure out the e-mail address and poster's name
	self.author, self.email=message.getaddr('From')
	e=message.getheader('Reply-To')
	if e!=None: self.email=e
	self.email=strip_separators(self.email)
	self.author=strip_separators(self.author)

	if self.author=="": self.author=self.email

	# Save the 'In-Reply-To:' and 'References:' lines
	i_r_t=message.getheader('In-Reply-To')
	if i_r_t==None: self.in_reply_to=''
	else:
	    match=msgid_pat.search(i_r_t)
	    if match==None: self.in_reply_to=''
	    else: self.in_reply_to=strip_separators(match.group(1))
		
	references=message.getheader('References')
	if references==None: self.references=[]
	else: self.references=map(strip_separators, string.split(references))

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
    def __repr__(self):
	return '<Article ID='+repr(self.msgid)+'>'

# Pipermail formatter class

class T:
    DIRMODE=0755      # Mode to give to created directories
    FILEMODE=0644     # Mode to give to created files
    INDEX_EXT = ".html" # Extension for indexes

    def __init__(self, basedir=None, reload=1, database=None):
	# If basedir isn't provided, assume the current directory
	if basedir==None: self.basedir=os.getcwd()
	else: 
            basedir=os.path.expanduser(basedir)
	    self.basedir=basedir
	self.database=database

	# If the directory doesn't exist, create it
	try: os.stat(self.basedir)
	except os.error, errdata:
	    errno, errmsg = errdata
	    if errno!=2: raise os.error, errdata
	    else: 
		self.message('Creating archive directory '+self.basedir)
		os.mkdir(self.basedir, self.DIRMODE)

	# Try to load previously pickled state
	try:
	    if not reload: raise IOError
	    f=open(os.path.join(self.basedir, 'pipermail.pck'), 'r')
	    self.message('Reloading pickled archive state')
	    d=pickle.load(f)
	    f.close()
	    for key, value in d.items(): setattr(self, key, value)
	except IOError: 
	    # No pickled version, so initialize various attributes
	    self.archives=[]        # Archives 
	    self._dirty_archives=[]  # Archives that will have to be updated
	    self.sequence=0         # Sequence variable used for numbering articles
	    self.update_TOC=0       # Does the TOC need updating?

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
	pickle.dump(self.__dict__, f)
	f.close()

    # 
    # Private methods 
    # 
    # These will be neither overridden nor called by custom archivers.
    #

	
    # Create a dictionary of various parameters that will be passed 
    # to the write_index_{header,footer} functions
    def __set_parameters(self, archive):
	import time
	# Determine the earliest and latest date in the archive
	firstdate=self.database.firstdate(archive)
	lastdate=self.database.lastdate(archive)

	# Get the current time
	now=time.asctime(time.localtime(time.time()))	
	self.firstdate=firstdate ; self.lastdate=lastdate
	self.archivedate=now ; self.size=self.database.numArticles(archive)
	self.archive=archive ; self.version=__version__

    # Find the message ID of an article's parent, or return None
    # if no parent can be found.

    def __findParent(self, article, children=[]):
	    parentID=None
	    if article.in_reply_to!='': parentID=article.in_reply_to
	    elif article.references!=[]: 
		# Remove article IDs that aren't in the archive
		refs=filter(self.articleIndex.has_key, article.references)
		if len(refs):
		    refs=map(lambda x, s=self: s.database.getArticle(s.archive, x), refs)
		    maxdate=refs[0]
		    for i in refs[1:]: 
			if i.date>maxdate.date: maxdate=i
		    parentID=maxdate.msgid
	    else:
		# Look for the oldest matching subject
		try: 
		    key, tempid=self.subjectIndex.set_location(article.subject)
		    print key, tempid
		    self.subjectIndex.next()	
		    [subject, date]= string.split(key, '\0')
		    print article.subject, subject, date
		    if (subject==article.subject and tempid not in children):
			parentID=tempid
		except KeyError: pass
	    return parentID

    # Update the threaded index completely
    def updateThreadedIndex(self):
	import pickle, sys
	# Erase the threaded index
	self.database.clearIndex(self.archive, 'thread')
	
	# Loop over all the articles 
	msgid=self.database.first(self.archive, 'date')
	while (msgid != None):
  	    article=self.database.getArticle(self.archive, msgid)
	    if article.parentID==None or not self.database.hasArticle(self.archive, article.parentID): 
		key=article.date
	    else: 
		parent=self.database.getArticle(self.archive, article.parentID)
		article.threadKey=parent.threadKey+article.date+'-' 
   	    self.database.setThreadKey(self.archive, article.threadKey+'\000'+article.msgid, msgid)
	    msgid=self.database.next(self.archive, 'date')

## 	    L1=[] ; L2=[]
## 	    while (1):
## 		article=self.database.getArticle(self.archive, msgid)
## 		L1.append('') ; L2.append(msgid) 
## 		L1=map(lambda x, d=article.date: d+'-'+x, L1)
## 		parentID=self.__findParent(article, L2)
## 		if parentID==None or not self.database.hasArticle(parentID): 
## 		    break
## 		else: msgid=parentID
## 	    for i in range(0, len(L1)):
## 		self.database.setThreadKey(self.archive, L1[i], '\000'+L2[i])
## 		self.database.setThreadKey(self.archive, '\000'+L2[i], L1[i])

    #
    # Public methods:
    #
    # These are part of the public interface of the T class, but will
    # never be overridden (unless you're trying to do something very new).
    
    # Update a single archive's indices, whether the archive's been
    # dirtied or not. 
    def update_archive(self, archive):	
	self.archive=archive
	self.message("Updating index files for archive ["+archive+']')
	arcdir=os.path.join(self.basedir, archive)
	parameters=self.__set_parameters(archive)
	# Handle the 3 simple indices first
	for i in ['Date', 'Subject', 'Author']:
	    self.message("  "+i)
	    self.type=i
	    # Get the right index
	    i=string.lower(i)

	    # Redirect sys.stdout
	    import sys
	    f=open(os.path.join(arcdir, i+self.INDEX_EXT), 'w')
	    os.chmod(f.name, self.FILEMODE)
	    temp_stdout, sys.stdout=sys.stdout, f
	    self.write_index_header()
	    count=0
	    # Loop over the index entries
	    finished=0
	    msgid=self.database.first(archive, i)
	    while (msgid != None):
		article=self.database.getArticle(self.archive, msgid)
		count=count+1
		self.write_index_entry(article)
		msgid = self.database.next(archive, i )
	    # Finish up this index
	    self.write_index_footer()
	    sys.stdout=temp_stdout
	    f.close()

	# Print the threaded index
	self.message("  Thread")
 	temp_stdout, sys.stdout=sys.stdout, open(os.path.join(arcdir, 'thread' + self.INDEX_EXT), 'w')
	os.chmod(os.path.join(arcdir, 'thread' + self.INDEX_EXT), self.FILEMODE)
 	self.type='Thread'
 	self.write_index_header()

	# To handle the prev./next in thread pointers, we need to
	# track articles 5 at a time.  

	# Get the first 5 articles	
	L=[ None ]*5 ; i=2 ; finished=0
	msgid=self.database.first(self.archive, 'thread')
	while msgid!=None and i<5:
	    L[i]=self.database.getArticle(self.archive, msgid) ; i=i+1
	    msgid = self.database.next(self.archive, 'thread')

	while L[2]!=None:
 	    article=L[2] ; artkey=None
	    if article!=None: artkey=article.threadKey
	    if artkey!=None: 
		import sys
		self.write_threadindex_entry(article, string.count(artkey, '-')-1)
		if self.database.changed.has_key( (archive,article.msgid) ):
		    a1=L[1] ; a3=L[3]
		    self.update_article(arcdir, article, a1, a3) 
		    if a3!=None: self.database.changed[ (archive,a3.msgid) ]=None
		    if a1!=None:
			if not self.database.changed.has_key( (archive,a1.msgid) ): 
			    self.update_article(arcdir, a1, L[0], L[2])
			else: del self.database.changed[ (archive,a1.msgid) ]
	    L=L[1:]			# Rotate the list
	    if msgid==None: L.append(msgid)
	    else: L.append( self.database.getArticle(self.archive, msgid) )
	    msgid = self.database.next(self.archive, 'thread')
	    
 	self.write_index_footer()
 	sys.stdout=temp_stdout

    # Update only archives that have been marked as "changed".
    def update_dirty_archives(self):
	for i in self._dirty_archives: self.update_archive(i)
	self._dirty_archives=[]

    # Read a Unix mailbox file from the file object <input>,
    # and create a series of Article objects.  Each article
    # object will then be archived.
    
    def processUnixMailbox(self, input, articleClass=Article):
	import mailbox
	mbox=mailbox.UnixMailbox(input)
	while (1):
	    m=mbox.next()
	    if not m: break			# End of file reached
	    a=articleClass(m, self.sequence) # Create an article object
	    self.sequence=self.sequence+1  # Increment the archive's sequence number
	    self.add_article(a)		# Add the article

    # Archive an Article object.
    def add_article(self, article):
	# Determine into what archives the article should be placed
	archives=self.get_archives(article)
	if archives==None: archives=[]        # If no value was returned, ignore it
	if type(archives)==type(''): archives=[archives] 	# If a string was returned, convert to a list
	if archives==[]: return         # Ignore the article

	# Add the article to each archive in turn
	article.filename=filename=self.get_filename(article)
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
			os.mkdir(archivedir, self.DIRMODE)
		    else: raise os.error, errdata
		self.open_new_archive(i, archivedir)
		
	    # Write the HTML-ized article
	    f=open(os.path.join(archivedir, filename), 'w')
	    os.chmod(os.path.join(archivedir, filename), self.FILEMODE)
	    temp_stdout, sys.stdout = sys.stdout, f
	    self.write_article_header(temp)
	    sys.stdout.writelines(temp.body)
	    self.write_article_footer(temp)
	    sys.stdout=temp_stdout
	    f.close()

	    authorkey=fixAuthor(article.author)+'\000'+article.date
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

    # Abstract methods: these will need to be overridden by subclasses
    # before anything useful can be done.

    def get_filename(self, article): 
	pass
    def get_archives(self, article):
	"""Return a list of indexes where the article should be filed.
	A string can be returned if the list only contains one entry, 
	and the empty list is legal."""
	pass
    def format_article(self, article):
	pass
    def write_index_header(self):
	pass
    def write_index_footer(self):
	pass
    def write_index_entry(self, article):
	pass
    def write_threadindex_entry(self, article, depth):
	pass
    def write_article_header(self, article):
	pass
    def write_article_footer(self, article):
	pass
    def write_article_entry(self, article):
	pass
    def update_article(self, archivedir, article, prev, next):
	pass
    def write_TOC(self):
	pass
    def open_new_archive(self, archive, dir):
	pass
    def message(self, msg):
	pass


class BSDDBdatabase(Database):
    def __init__(self, basedir):
	self.__cachekeys=[] ; self.__cachedict={}
	self.__currentOpenArchive=None   # The currently open indices
	self.basedir=os.path.expanduser(basedir)
	self.changed={}         # Recently added articles, indexed only by message ID
    def firstdate(self, archive):
	import time
	self.__openIndices(archive)
	date='None'
	try:
	    date, msgid = self.dateIndex.first()
	    date=time.asctime(time.localtime(string.atof(date)))
	except KeyError: pass
	return date
    def lastdate(self, archive):
	import time
	self.__openIndices(archive)
	date='None'
	try:
	    date, msgid = self.dateIndex.last()
	    date=time.asctime(time.localtime(string.atof(date)))
	except KeyError: pass
	return date
    def numArticles(self, archive):
	self.__openIndices(archive)
	return len(self.dateIndex)    

    # Add a single article to the internal indexes for an archive.

    def addArticle(self, archive, article, subjectkey, authorkey):
	import pickle
	self.__openIndices(archive)

	# Add the new article
	self.dateIndex[article.date]=article.msgid
	self.authorIndex[authorkey]=article.msgid
	self.subjectIndex[subjectkey]=article.msgid
	# Set the 'body' attribute to empty, to avoid storing the whole message
	temp = article.body ; article.body=[]
	self.articleIndex[article.msgid]=pickle.dumps(article)
	article.body=temp
	self.changed[archive,article.msgid]=None

	parentID=article.parentID
	if parentID!=None and self.articleIndex.has_key(parentID): 
	    parent=self.getArticle(archive, parentID)
	    myThreadKey=parent.threadKey+article.date+'-'
	else: myThreadKey = article.date+'-'
	article.threadKey=myThreadKey
	self.setThreadKey(archive, myThreadKey+'\000'+article.msgid, article.msgid)

    # Open the BSDDB files that are being used as indices
    # (dateIndex, authorIndex, subjectIndex, articleIndex)
    def __openIndices(self, archive):
	if self.__currentOpenArchive==archive: return

	import bsddb
	self.__closeIndices()
#	print 'opening indices for [%s]' % (repr(archive),)
	arcdir=os.path.join(self.basedir, 'database')
	try: os.mkdir(arcdir, 0700)
	except os.error: pass
	for i in ['date', 'author', 'subject', 'article', 'thread']:
	    t=bsddb.btopen(os.path.join(arcdir, archive+'-'+i), 'c') 
	    setattr(self, i+'Index', t)
	self.__currentOpenArchive=archive

    # Close the BSDDB files that are being used as indices (if they're
    # open--this is safe to call if they're already closed)
    def __closeIndices(self):
	if self.__currentOpenArchive!=None: 
	    pass
#	    print 'closing indices for [%s]' % (repr(self.__currentOpenArchive),)
	for i in ['date', 'author', 'subject', 'thread', 'article']:
	    attr=i+'Index'
	    if hasattr(self, attr): 
		index=getattr(self, attr) 
		if i=='article': 
	            if not hasattr(self, 'archive_length'): self.archive_length={}
		    self.archive_length[self.__currentOpenArchive]=len(index)
		index.close() 
		delattr(self,attr)
	self.__currentOpenArchive=None
    def close(self):
	self.__closeIndices()
    def hasArticle(self, archive, msgid): 
	self.__openIndices(archive)
	return self.articleIndex.has_key(msgid)
    def setThreadKey(self, archive, key, msgid):
	self.__openIndices(archive)
	self.threadIndex[key]=msgid
    def getArticle(self, archive, msgid):
	self.__openIndices(archive)
	if self.__cachedict.has_key(msgid): 
	    self.__cachekeys.remove(msgid)
	    self.__cachekeys.append(msgid)
	    return self.__cachedict[msgid]
	if len(self.__cachekeys)==CACHESIZE: 
	    delkey, self.__cachekeys = self.__cachekeys[0], self.__cachekeys[1:]
	    del self.__cachedict[delkey]
	s=self.articleIndex[msgid]
	article=pickle.loads(s)
	self.__cachekeys.append(msgid) ; self.__cachedict[msgid]=article
	return article

    def first(self, archive, index): 
	self.__openIndices(archive)
	index=getattr(self, index+'Index')
	try: 
	    key, msgid = index.first()
	    return msgid
	except KeyError: return None
    def next(self, archive, index): 
	self.__openIndices(archive)
	index=getattr(self, index+'Index')
	try: 
	    key, msgid = index.next()
	    return msgid
	except KeyError: return None
	
    def getOldestArticle(self, archive, subject):
	self.__openIndices(archive)
	subject=string.lower(subject)
	try: 
	    key, tempid=self.subjectIndex.set_location(subject)
	    self.subjectIndex.next()	
	    [subject2, date]= string.split(key, '\0')
	    if subject!=subject2: return None
	    return tempid
	except KeyError: 
	    return None

    def newArchive(self, archive): pass
    def clearIndex(self, archive, index):
	self.__openIndices(archive)
	index=getattr(self, index+'Index')
	finished=0
	try:
	    key, msgid=self.threadIndex.first()	    		
	except KeyError: finished=1
	while not finished:
	    del self.threadIndex[key]
	    try:
		key, msgid=self.threadIndex.next()	    		
	    except KeyError: finished=1


