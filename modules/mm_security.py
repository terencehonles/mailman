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


"""Handle passwords and sanitize approved messages."""


import crypt, types, string, os
import mm_err, mm_utils, mm_cfg

# TBD: is this the best location for the site password?
SITE_PW_FILE = os.path.join(mm_cfg.DATA_DIR, 'adm.pw')


class SecurityManager:
    def SetSiteAdminPassword(self, pw):
    	old = os.umask(0022)
	f = open(SITE_PW_FILE, "w+")
	f.write(crypt.crypt(pw, mm_utils.GetRandomSeed()))
	f.close()
        os.umask(old)

    def CheckSiteAdminPassword(self, str):
	try:
	    f = open(SITE_PW_FILE, "r+")
	    pw = f.read()
	    f.close()
	    return crypt.crypt(str, pw) == pw
	# There probably is no site admin password if there was an exception
	except: 
	    return 0

    def InitVars(self, crypted_password):
	# Configurable, however, we don't pass this back in GetConfigInfo
	# because it's a special case as it requires confirmation to change.
	self.password = crypted_password      

	# Non configurable
	self.passwords = {}

    def ValidAdminPassword(self, pw):
	if self.CheckSiteAdminPassword(pw):
            return 1
	return ((type(pw) == types.StringType) and 
		(crypt.crypt(pw, self.password) == self.password))

    def ConfirmAdminPassword(self, pw):
	if(not self.ValidAdminPassword(pw)):
	    raise mm_err.MMBadPasswordError
	return 1

    def ConfirmUserPassword(self, user, pw):
	if self.ValidAdminPassword(pw):
	    return 1
	if not user in self.members and not user in self.digest_members:
	    user = self.FindUser(user)
        try:
            if string.lower(pw) <> string.lower(self.passwords[user]):
                raise mm_err.MMBadPasswordError
        except KeyError:
            raise mm_err.MMBadUserError
	return 1

    def ChangeUserPassword(self, user, newpw, confirm):
	self.IsListInitialized()
	addr = self.FindUser(user)
	if not addr:
	    raise mm_err.MMNotAMemberError
	if newpw <> confirm:
	    raise mm_err.MMPasswordsMustMatch
	self.passwords[addr] = newpw
	self.Save()

    def ExtractApproval(self, msg):
        """True if message has valid administrator approval.

        Approval line is always stripped from message as a side effect."""

        p = msg.getheader('approved')
        if p == None:
            return 0
        del msg['approved']         # Mustn't deliver this line!!
        return self.ValidAdminPassword(p)
