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

"""Queue up posts if the SMTP connection fails."""

import tempfile, marshal, mm_cfg

TEMPLATE = "mm_q."

def dequeueMessage(msg):
    import os
    os.unlink(msg)

def processQueue():
    import os, smtplib
    files = os.listdir(mm_cfg.DATA_DIR)
    for file in files:
        if TEMPLATE <> file[:len(TEMPLATE)]:
            continue
        full_fname = os.path.join(mm_cfg.DATA_DIR, file)
        f = open(full_fname,"r")
        recip,sender,text = marshal.load(f)
        f.close()
        import Utils
        Utils.TrySMTPDelivery(recip,sender,text,full_fname)
        
            
def enqueueMessage(the_sender, recip, text):
    tempfile.tempdir = mm_cfg.DATA_DIR
    tempfile.template = TEMPLATE
    fname = tempfile.mktemp()
    f = open(fname, "a+")
    marshal.dump((recip,the_sender,text),f)
    f.close()
    return fname
