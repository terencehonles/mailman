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


import os
import string
import time
import types
import Crypt
import Errors
import Utils
import Cookie
from urlparse import urlparse
import mm_cfg

# TBD: is this the best location for the site password?
SITE_PW_FILE = os.path.join(mm_cfg.DATA_DIR, 'adm.pw')


class SecurityManager:
    def SetSiteAdminPassword(self, pw):
    	old = os.umask(0022)
	f = open(SITE_PW_FILE, "w+")
	f.write(Crypt.crypt(pw, Utils.GetRandomSeed()))
	f.close()
        os.umask(old)

    def CheckSiteAdminPassword(self, str):
	try:
	    f = open(SITE_PW_FILE, "r")
	    pw = f.read()
	    f.close()
	    return Crypt.crypt(str, pw) == pw
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
		(Crypt.crypt(pw, self.password) == self.password))

    def ConfirmAdminPassword(self, pw):
	if(not self.ValidAdminPassword(pw)):
	    raise Errors.MMBadPasswordError
	return 1

    def WebAuthenticate(self, user=None, password=None, cookie=None):
        if cookie:
            cookie_key = self._internal_name + ':' + cookie
        else:
            cookie_key = self._internal_name
        if password is not None:  # explicit login
            if user:
                self.ConfirmUserPassword(user, password)
            else:
                self.ConfirmAdminPassword(password)
            print self.MakeCookie(cookie_key)
            return 1
        else:
            return self.CheckCookie(cookie_key)

    def MakeCookie(self, key):
        # Make sure we have the necessary ingredients for our cookie
        client_ip = os.environ.get('REMOTE_ADDR') or '0.0.0.0'
        issued = int(time.time())
        expires = issued + mm_cfg.ADMIN_COOKIE_LIFE
        # ... including the secret ingredient :)
        secret = self.password
        mac = hash(secret + client_ip + `issued` + `expires`)
        # Mix all ingredients gently together,
        c = Cookie.Cookie()
        c[key] = [client_ip, issued, expires, mac]
        # place in oven,
        path = urlparse(mm_cfg.DEFAULT_URL)[2] # '/mailman'
        c[key]['path'] = path
        # and bake until golden brown
        c[key]['expires'] = mm_cfg.ADMIN_COOKIE_LIFE
        return c

    def CheckCookie(self, key):
        if not os.environ.has_key('HTTP_COOKIE'):
            return 0
        c = Cookie.Cookie(os.environ['HTTP_COOKIE'])
        if not c.has_key(key):
            return 0
        cookie = c[key].value
        if (type(cookie) <> type([]) or
            len(cookie) <> 4):
            raise Errors.MMInvalidCookieError
        client_ip = os.environ.get('REMOTE_ADDR') or '0.0.0.0'
        now = time.time()
        [for_ip, issued, expires, received_mac] = cookie
        if (for_ip <> client_ip or now < issued):
            raise Errors.MMInvalidCookieError
        if now > expires:
            raise Errors.MMExpiredCookieError
        secret = self.password
        mac = hash(secret + client_ip + `issued` + `expires`)
        if mac <> received_mac:
            raise Errors.MMInvalidCookieError
        return 1

    def ConfirmUserPassword(self, user, pw):
        """True if password is valid for site, list admin, or specific user."""
        if self.ValidAdminPassword(pw):
            return 1
        addr = self.FindUser(user)
        if addr is None:
            raise Errors.MMNotAMemberError
        storedpw = self.passwords.get(addr)
        if storedpw is None:
            raise Errors.MMBadUserError
        if storedpw <> pw:
            raise Errors.MMBadPasswordError
        return 1

    def ChangeUserPassword(self, user, newpw, confirm):
	self.IsListInitialized()
	addr = self.FindUser(user)
	if not addr:
	    raise Errors.MMNotAMemberError
	if newpw <> confirm:
	    raise Errors.MMPasswordsMustMatch
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
