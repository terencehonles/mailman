# Copyright (C) 2000,2001 by the Free Software Foundation, Inc.
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

"""Reading and writing message objects and message metadata.
"""

# enqueue() and dequeue() are not symmetric.  enqueue() takes a Message
# object.  dequeue() returns a mimelib.Message object tree.
#
# Message metadata is represented internally as a Python dictionary.  Keys and
# values must be strings.  When written to a queue directory, the metadata is
# written into an externally represented format, as defined here.  Because
# components of the Mailman system may be written in something other than
# Python, the external interchange format should be chosen based on what those
# other components can read and write.
#
# Most efficient, and recommended if everything is Python, is Python marshal
# format.  Also supported by default is Berkeley db format (using the default
# bsddb module compiled into your Python executable -- usually Berkeley db
# 2), and rfc822 style plain text.  You can write your own if you have other
# needs.

import os
import time
import sha
import marshal
from errno import EEXIST

from mimelib.Parser import Parser

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Message
from Mailman.Logging.Syslog import syslog

# 20 bytes of all bits set, maximum sha.digest() value
shamax = 0xffffffffffffffffffffffffffffffffffffffffL



class _Switchboard:
    def __init__(self, whichq, slice=None, numslices=1):
        self.__whichq = whichq
        # Create the directory if it doesn't yet exist.
        # FIXME
        omask = os.umask(0)                       # rwxrws---
        try:
            try:
                os.mkdir(self.__whichq, 0770)
            except OSError, e:
                if e.errno <> EEXIST: raise
        finally:
            os.umask(omask)
        # Fast track for no slices
        self.__lower = None
        self.__upper = None
        # BAW: test performance and end-cases of this algorithm
        if numslices <> 1:
            self.__lower = (shamax * slice) / numslices
            self.__upper = (shamax * (slice+1)) / numslices

    def enqueue(self, _msg, _metadata={}, **_kws):
        # Calculate the SHA hexdigest of the message to get a unique base
        # filename.
        data = _metadata.copy()
        data.update(_kws)
        listname = data.get('listname', '--nolist--')
        now = `time.time()`
        msgtext = str(_msg)
        hashfood = msgtext + listname + now
        filebase = sha.new(hashfood).hexdigest()
        # Figure out which queue files the message is to be written to.
        msgfile = os.path.join(self.__whichq, filebase + '.msg')
        dbfile = os.path.join(self.__whichq, filebase + '.db')
        # Always add the metadata schema version number
        data['version'] = mm_cfg.QFILE_SCHEMA_VERSION
        # Filter out volatile entries
        for k in data.keys():
            if k[0] == '_':
                del data[k]
        # Now write the message text to one file and the metadata to another
        # file.  The metadata is always written second to avoid race
        # conditions with the various queue runners (which key off of the .db
        # filename).
        omask = os.umask(007)                     # -rw-rw----
        try:
            msgfp = open(msgfile, 'w')
        finally:
            os.umask(omask)
        msgfp.write(msgtext)
        msgfp.close()
        # Now write the metadata using the appropriate external metadata
        # format.  We play rename-switcheroo here to further plug the race
        # condition holes.
        tmpfile = dbfile + '.tmp'
        self._ext_write(tmpfile, data)
        os.rename(tmpfile, dbfile)

    def dequeue(self, filebase):
        # Calculate the .db and .msg filenames from the given filebase.
        msgfile = os.path.join(self.__whichq, filebase + '.msg')
        dbfile = os.path.join(self.__whichq, filebase + '.db')
        # Read the message text and parse it into a message object tree.  When
        # done, unlink the msg file.
        msgfp = open(msgfile)
        p = Parser(_class=Message.Message)
        msg = p.parse(msgfp)
        msgfp.close()
        os.unlink(msgfile)
        # Now, read the metadata using the appropriate external metadata
        # format.  When done, unlink the metadata file.
        data = self._ext_read(dbfile)
        os.unlink(dbfile)
        return msg, data

    def files(self):
        all = [os.path.splitext(f)[0] for f in os.listdir(self.__whichq)
               if f.endswith('.db')]
        # Fast track exit
        if self.__lower is None:
            return all
        # BAW: test performance and end-cases of this algorithm
        return [f for f in all if self.__lower <= long(f, 16) < self.__upper]

    def _ext_write(self, tmpfile, data):
        raise UnimplementedError

    def _ext_read(self, dbfile):
        raise UnimplementedError



class MarshalSwitchboard(_Switchboard):
    """Python marshal format."""
    def _ext_write(self, filename, dict):
        omask = os.umask(007)                     # -rw-rw----
        try:
            fp = open(filename, 'w')
        finally:
            os.umask(omask)
        marshal.dump(dict, fp)
        fp.close()

    def _ext_read(self, filename):
        fp = open(filename)
        data = marshal.load(fp)
        fp.close()
        return data



class BSDDBSwitchboard(_Switchboard):
    """Native (i.e. compiled-in) Berkeley db format."""
    def _ext_write(self, filename, dict):
        import bsddb
        omask = os.umask(0)
        try:
            hashfile = bsddb.hashopen(filename, 'n', 0660)
        finally:
            os.umask(omask)
        # values must be strings
        for k, v in dict.items():
            hashfile[k] = marshal.dumps(v)
        hashfile.sync()
        hashfile.close()

    def _ext_read(self, filename):
        import bsddb
        dict = {}
        hashfile = bsddb.hashopen(filename, 'r')
        for k in hashfile.keys():
            dict[k] = marshal.loads(hashfile[k])
        hashfile.close()
        return dict



class ASCIISwitchboard(_Switchboard):
    """Human readable .db file format.

    key/value pairs are written as

        key = value

    as real Python code which can be execfile'd.
    """

    def _ext_write(self, filename, dict):
        omask = os.umask(007)                     # -rw-rw----
        try:
            fp = open(filename, 'w')
        finally:
            os.umask(omask)
        for k, v in dict.items():
            print >> fp, '%s = %s' % (k, repr(v))
        fp.close()

    def _ext_read(self, filename):
        dict = {'__builtins__': {}}
        execfile(filename, dict)
        del dict['__builtins__']
        return dict



# Here are the various types of external file formats available.  The format
# chosen is given defined in the mm_cfg.py configuration file.
if mm_cfg.METADATA_FORMAT == mm_cfg.METAFMT_MARSHAL:
    Switchboard = MarshalSwitchboard
elif mm_cfg.METADATA_FORMAT == mm_cfg.METAFMT_BSDDB_NATIVE:
    Switchboard = BSDDBSwitchboard
elif mm_cfg.METADATA_FORMAT == mm_cfg.METAFMT_ASCII:
    Switchboard = ASCIISwitchboard
else:
    syslog('error', 'Undefined metadata format: %d (using marshals)' %
           mm_cfg.METADATA_FORMAT)
    Switchboard = MarshalSwitchboard
