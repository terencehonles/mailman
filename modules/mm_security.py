import crypt, types, string, os
import mm_err, mm_utils, mm_cfg

class SecurityManager:
    def SetSiteAdminPassword(self, pw):
    	old = os.umask(0700)
	f = open(os.path.join(mm_cfg.MAILMAN_DIR, "adm.pw"), "w+")
	f.write(crypt.crypt(pw, mm_utils.GetRandomSeed()))
	f.close()
        os.umask(old)

    def CheckSiteAdminPassword(self, str):
	try:
	    f = open(os.path.join(mm_cfg.MAILMAN_DIR, "adm.pw"), "r+")
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
	if string.lower(pw) <> string.lower(self.passwords[user]):
	    raise mm_err.MMBadPasswordError
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

