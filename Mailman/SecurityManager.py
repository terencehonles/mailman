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
import time
from types import StringType, ListType
import md5
from urlparse import urlparse

from Mailman import Crypt
from Mailman import Errors
from Mailman import Utils
from Mailman import Cookie
from Mailman import mm_cfg

# TBD: is this the best location for the site password?
SITE_PW_FILE = os.path.join(mm_cfg.DATA_DIR, 'adm.pw')


class SecurityManager:
    def SetSiteAdminPassword(self, pw):
        fp = Utils.open_ex(SITE_PW_FILE, 'w', perms=0640)
        fp.write(Crypt.crypt(pw, Utils.GetRandomSeed()))
        fp.close()

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
	return type(pw) == StringType and \
               Crypt.crypt(pw, self.password) == self.password

    def ConfirmAdminPassword(self, pw):
        if not self.ValidAdminPassword(pw):
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
        issued = time.time()
        expires = int(issued) + mm_cfg.ADMIN_COOKIE_LIFE
        # ... including the secret ingredient :)
        secret = self.password
        mac = md5.new(secret + `issued` + `expires`).digest()
        # Mix all ingredients gently together,
        c = Cookie.Cookie()
        c[key] = [issued, expires, mac]
        # place in oven,
        path = urlparse(self.web_page_url)[2] # '/mailman'
        c[key]['path'] = path
        # and bake until golden brown
        c[key]['expires'] = mm_cfg.ADMIN_COOKIE_LIFE
        return c

    def CheckCookie(self, key):
        cookiedata = os.environ.get('HTTP_COOKIE')
        if not cookiedata:
            return 0
        #
        # TBD: At least some versions of MS Internet Explorer stores cookies
        # without the double quotes.  This has been verified for MSIE 4.01,
        # although MSIE 5 is fixed.  The bug (see PR#80) is that if these
        # double quotes are missing, the cookie data does not unpickle into
        # the list that we expect.  The kludge given here (slightly modified)
        # was initially provided by Evaldas Auryla <evaldas.auryla@pheur.org>
        #
        keylen = len(key)
        try:
            if cookiedata[keylen+1] <> '"' and cookiedata[-1] <> '"':
                cookiedata = key + '="' + cookiedata[keylen+1:] + '"'
        except IndexError:
            # cookiedata got truncated somehow; just let it fail normally
            pass
        c = Cookie.Cookie(cookiedata)
        if not c.has_key(key):
            return 0
        cookie = c[key].value
        if type(cookie) <> ListType or len(cookie) <> 3:
            raise Errors.MMInvalidCookieError
        now = time.time()
        [issued, expires, received_mac] = cookie
        if now < issued:
            raise Errors.MMInvalidCookieError
        if now > expires:
            raise Errors.MMExpiredCookieError
        secret = self.password
        mac = md5.new(secret + `issued` + `expires`).digest()
        if mac <> received_mac:
            raise Errors.MMInvalidCookieError
        return 1

    def ConfirmUserPassword(self, user, pw):
        """True if password is valid for site, list admin, or specific user."""
        if self.ValidAdminPassword(pw):
            return 1
        if user is None:
            raise Errors.MMBadUserError
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

        Approval line is always stripped from message as a side effect.
        """
        p = msg.getheader('approved')
        if p is None:
            return 0
        del msg['approved']         # Mustn't deliver this line!!
        return self.ValidAdminPassword(p)
