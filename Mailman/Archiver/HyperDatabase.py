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

#
# site modules
#
import os
import marshal
import string

#
# package/project modules
#
import pipermail
from Mailman import LockFile
from Mailman.Utils import mkdir, open_ex
# TBD: ugly, ugly, ugly -baw
open = open_ex

CACHESIZE = pipermail.CACHESIZE

try:
    import cPickle
    pickle = cPickle
except ImportError:
    import pickle


#
# we're using a python dict in place of
# of bsddb.btree database.  only defining
# the parts of the interface used by class HyperDatabase
# only one thing can access this at a time.
#
class DumbBTree:
    # XXX This dictionary-like object stores pickles of all the
    # Article objects.  The object itself is stored using marshal.  It 
    # would be much simpler, and probably faster, to store the actual
    # objects in the DumbBTree and pickle it.
    # XXX Also needs a more sensible name, like IteratableDictionary
    # or SortedDictionary.
    def __init__(self, path):
        self.current_index = 0
        self.path = path
        self.lockfile = LockFile.LockFile(self.path + ".lock")
        self.lock()
        self.__dirty = 0
        if os.path.exists(path):
            self.dict = marshal.load(open(path))
            self.__sort(dirty=1)
        else:
            self.dict = {}
            self.sorted = []

    def __sort(self, dirty=None):
        if self.__dirty == 1 or dirty:
            self.sorted = self.dict.keys()
            self.sorted.sort()
            self.__dirty = 0
        
    def lock(self):
        self.lockfile.lock()

    def unlock(self):
        try:
            self.lockfile.unlock()
        except LockFile.NotLockedError:
            pass
        
    def __delitem__(self, item):
        # if first hasn't been called, we can skip the sort
        if self.current_index == 0:
            del self.dict[item]
            self.__dirty = 1
            return
	try:
	    ci = self.sorted[self.current_index]
	except IndexError:
	    ci = None
	if ci == item:
	    try:
		ci = self.sorted[self.current_index + 1]
	    except IndexError:
		ci = None
	del self.dict[item]
        self.__sort(dirty=1)
	if ci is not None:
	    self.current_index = self.sorted.index(ci)
	else:
	    self.current_index = self.current_index + 1

    def clear(self):
        # bulk clearing much faster than deleting each item, esp. with the
        # implementation of __delitem__() above :(
        self.dict = {}

    def first(self):
        self.__sort() # guarantee that the list is sorted
        if not self.sorted:
            raise KeyError
        else:
            key = self.sorted[0]
            res = key, self.dict[key]
            self.current_index = 1
	    return res

    def last(self):
        if not self.sorted:
            raise KeyError
        else:
            key = self.sorted[-1]
	    self.current_index = len(self.sorted) - 1
            return key, self.dict[key]
	
    def next(self):
        try:
            key = self.sorted[self.current_index]
        except IndexError:
            raise KeyError
	self.current_index = self.current_index + 1
        return key, self.dict[key]

    def has_key(self, key):
        return self.dict.has_key(key)

    def set_location(self, loc):
        if not self.dict.has_key(loc):
            raise KeyError
        self.current_index = self.sorted.index(loc)

    def __getitem__(self, item):
        return self.dict[item]

    def __setitem__(self, item, val):
        # if first hasn't been called, then we don't need to worry
        # about sorting again
        if self.current_index == 0:
            self.dict[item] = val
            self.__dirty = 1
            return
	try:
	    current_item = self.sorted[self.current_index]
	except IndexError:
	    current_item = item
        self.dict[item] = val
        self.__sort(dirty=1)
        self.current_index = self.sorted.index(current_item)

    def __len__(self):
        return len(self.sorted)

    def close(self):
        fp = open(self.path, "w")
        fp.write(marshal.dumps(self.dict))
        fp.close()
        self.unlock()



# this is lifted straight out of pipermail with
# the bsddb.btree replaced with above class.
# didn't use inheritance because of all the
# __internal stuff that needs to be here -scott
#
class HyperDatabase(pipermail.Database):
    def __init__(self, basedir):
        self.__cache = {}
	self.__currentOpenArchive = None   # The currently open indices
	self.basedir = os.path.expanduser(basedir)
        # Recently added articles, indexed only by message ID
        self.changed={}

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
	self.__closeIndices()
	arcdir=os.path.join(self.basedir, 'database')
	try: mkdir(arcdir, mode=02770)
        except os.error: pass
	for i in ['date', 'author', 'subject', 'article', 'thread']:
	    t=DumbBTree(os.path.join(arcdir, archive+'-'+i)) 
	    setattr(self, i+'Index', t)
	self.__currentOpenArchive=archive

    # Close the BSDDB files that are being used as indices (if they're
    # open--this is safe to call if they're already closed)
    def __closeIndices(self):
	if self.__currentOpenArchive!=None: 
	    pass
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
        if not self.__cache.has_key(msgid):
            # get the pickled object out of the DumbBTree
            buf = self.articleIndex[msgid]
            article = self.__cache[msgid] = pickle.loads(buf)
        else:
            article = self.__cache[msgid]
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
##	index=getattr(self, index+'Index')
        if hasattr(self.threadIndex, 'clear'):
            self.threadIndex.clear()
            return
	finished=0
	try:
	    key, msgid=self.threadIndex.first()	    		
	except KeyError: finished=1
	while not finished:
	    del self.threadIndex[key]
	    try:
		key, msgid=self.threadIndex.next()	    		
	    except KeyError: finished=1











