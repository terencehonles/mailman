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


"""Handle passwords and sanitize approved messages."""


import os
import time
import sha
import marshal
from types import StringType, TupleType
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
        key = self.internal_name()
        if cookie:
            key = key + ':' + cookie
        # password will be None for explicit login
        if password is not None:
            if user:
                self.ConfirmUserPassword(user, password)
            else:
                self.ConfirmAdminPassword(password)
            print self.MakeCookie(key)
            return 1
        else:
            return self.CheckCookie(key)

    def MakeCookie(self, key):
        # Ingredients for our cookie: our `secret' which is the list's admin
        # password (never sent in the clear) and the time right now in seconds
        # since the epoch.
        secret = self.password
        issued = int(time.time())
        # Get a digest of the secret, plus other information.
        mac = sha.new(secret + `issued`).hexdigest()
        # Create the cookie object.  The way the cookie module converts
        # non-strings to pickles can cause problems if the resulting string
        # needs to be quoted.  So we'll do the conversion ourselves.
        c = Cookie.Cookie()
        c[key] = Utils.hexlify(marshal.dumps((issued, mac)))
        # The path to all Mailman stuff, minus the scheme and host,
        # i.e. usually the string `/mailman'
        path = urlparse(self.web_page_url)[2]
        c[key]['path'] = path
        # Should we use session or persistent cookies?
        if mm_cfg.ADMIN_COOKIE_LIFE > 0:
            c[key]['expires'] = mm_cfg.ADMIN_COOKIE_LIFE
            c[key]['max-age'] = mm_cfg.ADMIN_COOKIE_LIFE
        # Set the RFC 2109 required header
        c[key]['version'] = 1
        return c

    def ZapCookie(self, cookie=None):
        key = self.internal_name()
        if cookie:
            key = key + ':' + cookie
        # Logout of the session by zapping the cookie.  For safety both set
        # max-age=0 (as per RFC2109) and set the cookie data to the empty
        # string.
        c = Cookie.Cookie()
        c[key] = ''
        # The path to all Mailman stuff, minus the scheme and host,
        # i.e. usually the string `/mailman'
        path = urlparse(self.web_page_url)[2]
        c[key]['path'] = path
        c[key]['max-age'] = 0
        # Don't set expires=0 here otherwise it'll force a persistent cookie
        c[key]['version'] = 1
        return c

    def CheckCookie(self, key):
        cookiedata = os.environ.get('HTTP_COOKIE')
        if not cookiedata:
            return 0
        c = Cookie.Cookie(cookiedata)
        if not c.has_key(key):
            return 0
        # Undo the encoding we performed in MakeCookie() above
        try:
            cookie = marshal.loads(Utils.unhexlify(c[key].value))
            issued, received_mac = cookie
        except (EOFError, ValueError, TypeError):
            raise Errors.MMInvalidCookieError
        now = time.time()
        if now < issued:
            raise Errors.MMInvalidCookieError
        secret = self.password
        mac = sha.new(secret + `issued`).hexdigest()
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
