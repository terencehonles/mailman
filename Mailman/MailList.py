# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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


"""The class representing a Mailman mailing list.

Mixes in many task-specific classes.
"""

import sys
import os
import marshal
import errno
import re
import shutil
import socket
import urllib
from UserDict import UserDict
from urlparse import urlparse
from types import *

from mimelib.address import getaddresses, dump_address_pair
# We use this explicitly instead of going through mimelib so that we can pick
# up the RFC 2822-conformant version of rfc822.py that will be included in
# Python 2.2.
from Mailman.pythonlib.rfc822 import parseaddr

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import LockFile
from Mailman.UserDesc import UserDesc

# base classes
from Mailman.Archiver import Archiver
from Mailman.Autoresponder import Autoresponder
from Mailman.Bouncer import Bouncer
from Mailman.Deliverer import Deliverer
from Mailman.Digester import Digester
from Mailman.GatewayManager import GatewayManager
from Mailman.HTMLFormatter import HTMLFormatter 
from Mailman.ListAdmin import ListAdmin
from Mailman.MailCommandHandler import MailCommandHandler 
from Mailman.SecurityManager import SecurityManager
from Mailman.TopicMgr import TopicMgr

# gui components package
from Mailman import Gui

# other useful classes
from Mailman.OldStyleMemberships import OldStyleMemberships
from Mailman import Message
from Mailman import Pending
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO

EMPTYSTRING = ''



# Use mixins here just to avoid having any one chunk be too large.
class MailList(MailCommandHandler, HTMLFormatter, Deliverer, ListAdmin, 
               Archiver, Digester, SecurityManager, Bouncer, GatewayManager,
               Autoresponder, TopicMgr):

    #
    # A MailList object's basic Python object model support
    #
    def __init__(self, name=None, lock=1):
        # No timeout by default.  If you want to timeout, open the list
        # unlocked, then lock explicitly.
        #
        # Only one level of mixin inheritance allowed
        for baseclass in self.__class__.__bases__:
            if hasattr(baseclass, '__init__'):
                baseclass.__init__(self)
        # Initialize volatile attributes
        self.InitTempVars(name)
        # Default membership adaptor class
        self._memberadaptor = OldStyleMemberships(self)
        if name:
            if lock:
                # This will load the database.
                self.Lock()
            else:
                self.Load()
            # This extension mechanism allows list-specific overrides of any
            # method (well, except __init__(), InitTempVars(), and InitVars()
            # I think).
            filename = os.path.join(self._full_path, 'extend.py')
            dict = {}
            try:
                execfile(filename, dict)
            except IOError, e:
                if e.errno <> errno.ENOENT: raise
            else:
                dict['extend'](self)

    def __del__(self):
        try:
            self.Unlock()
        except AttributeError:
            # List didn't get far enough to have __lock
            pass

    def __getattr__(self, name):
        # Because we're using delegation, we want to be sure that attribute
        # access to a delegated member function gets passed to the
        # sub-objects.  This of course imposes a specific name resolution
        # order.
        try:
            return getattr(self._memberadaptor, name)
        except AttributeError:
            for guicomponent in self._gui:
                try:
                    return getattr(guicomponent, name)
                except AttributeError:
                    pass
            else:
                raise AttributeError, name

    def __repr__(self):
        if self.Locked():
            status = '(locked)'
        else:
            status = '(unlocked)'
        return '<mailing list "%s" %s at %x>' % (
            self.internal_name(), status, id(self))


    #
    # Lock management
    #
    def Lock(self, timeout=0):
        self.__lock.lock(timeout)
        # Must reload our database for consistency.  Watch out for lists that
        # don't exist.
        try:
            self.Load()
        except Exception:
            self.Unlock()
            raise
    
    def Unlock(self):
        self.__lock.unlock(unconditionally=1)

    def Locked(self):
        return self.__lock.locked()



    #
    # Useful accessors
    #
    def internal_name(self):
        return self._internal_name

    def fullpath(self):
        return self._full_path

    def GetAdminEmail(self):
        return '%s-admin@%s' % (self._internal_name, self.host_name)

    def GetOwnerEmail(self):
        return '%s-owner@%s' % (self._internal_name, self.host_name)

    def GetMemberAdminEmail(self, member):
        """Usually the member addr, but modified for umbrella lists.

        Umbrella lists have other mailing lists as members, and so admin stuff
        like confirmation requests and passwords must not be sent to the
        member addresses - the sublists - but rather to the administrators of
        the sublists.  This routine picks the right address, considering
        regular member address to be their own administrative addresses.

        """
        if not self.umbrella_list:
            return member
        else:
            acct, host = tuple(member.split('@'))
            return "%s%s@%s" % (acct, self.umbrella_member_suffix, host)

    def GetRequestEmail(self):
        return '%s-request@%s' % (self._internal_name, self.host_name)

    def GetListEmail(self):
        return '%s@%s' % (self._internal_name, self.host_name)

    def GetScriptURL(self, scriptname, absolute=0):
        return Utils.ScriptURL(scriptname, self.web_page_url, absolute) + \
               '/' + self.internal_name()

    def GetOptionsURL(self, user, obscure=0, absolute=0):
        url = self.GetScriptURL('options', absolute)
        if obscure:
            user = Utils.ObscureEmail(user)
        return '%s/%s' % (url, urllib.quote(user.lower()))


    #
    # Instance and subcomponent initialization
    #
    def InitTempVars(self, name):
        """Set transient variables of this and inherited classes."""
        self.__lock = LockFile.LockFile(
            os.path.join(mm_cfg.LOCK_DIR, name or '<site>') + '.lock',
            # TBD: is this a good choice of lifetime?
            lifetime = mm_cfg.LIST_LOCK_LIFETIME,
            withlogging = mm_cfg.LIST_LOCK_DEBUGGING)
        self._internal_name = name
        if name:
            self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
        else:
            self._full_path = None
        # Only one level of mixin inheritance allowed
        for baseclass in self.__class__.__bases__:
            if hasattr(baseclass, 'InitTempVars'):
                baseclass.InitTempVars(self)
        # Now, initialize our gui components
        self._gui = []
        for component in dir(Gui):
            if component.startswith('_'):
                continue
            self._gui.append(getattr(Gui, component)())

    def InitVars(self, name=None, admin='', crypted_password=''):
        """Assign default values - some will be overriden by stored state."""
        # Non-configurable list info 
        if name:
          self._internal_name = name

        # Must save this state, even though it isn't configurable
        self.volume = 1
        self.members = {} # self.digest_members is initted in mm_digest
        self.data_version = mm_cfg.DATA_FILE_VERSION
        self.last_post_time = 0
        
        self.post_id = 1.  # A float so it never has a chance to overflow.
        self.user_options = {}
        self.language = {}
        self.usernames = {}
        self.passwords = {}

        # This stuff is configurable
        self.dont_respond_to_post_requests = 0
        self.advertised = mm_cfg.DEFAULT_LIST_ADVERTISED
        self.max_num_recipients = mm_cfg.DEFAULT_MAX_NUM_RECIPIENTS
        self.max_message_size = mm_cfg.DEFAULT_MAX_MESSAGE_SIZE
        self.web_page_url = mm_cfg.DEFAULT_URL   
        self.owner = [admin]
        self.moderator = []
        self.reply_goes_to_list = mm_cfg.DEFAULT_REPLY_GOES_TO_LIST
        self.reply_to_address = ''
        self.posters = []
        self.forbidden_posters = []
        self.admin_immed_notify = mm_cfg.DEFAULT_ADMIN_IMMED_NOTIFY
        self.admin_notify_mchanges = \
                mm_cfg.DEFAULT_ADMIN_NOTIFY_MCHANGES
        self.moderated = mm_cfg.DEFAULT_MODERATED
        self.require_explicit_destination = \
                mm_cfg.DEFAULT_REQUIRE_EXPLICIT_DESTINATION
        self.acceptable_aliases = mm_cfg.DEFAULT_ACCEPTABLE_ALIASES
        self.umbrella_list = mm_cfg.DEFAULT_UMBRELLA_LIST
        self.umbrella_member_suffix = \
                mm_cfg.DEFAULT_UMBRELLA_MEMBER_ADMIN_SUFFIX
        self.send_reminders = mm_cfg.DEFAULT_SEND_REMINDERS
        self.send_welcome_msg = mm_cfg.DEFAULT_SEND_WELCOME_MSG
        self.bounce_matching_headers = \
                mm_cfg.DEFAULT_BOUNCE_MATCHING_HEADERS
        self.anonymous_list = mm_cfg.DEFAULT_ANONYMOUS_LIST
        internalname = self.internal_name()
        self.real_name = internalname[0].upper() + internalname[1:]
        self.description = ''
        self.info = ''
        self.welcome_msg = ''
        self.goodbye_msg = ''
        self.subscribe_policy = mm_cfg.DEFAULT_SUBSCRIBE_POLICY
        self.private_roster = mm_cfg.DEFAULT_PRIVATE_ROSTER
        self.obscure_addresses = mm_cfg.DEFAULT_OBSCURE_ADDRESSES
        self.member_posting_only = mm_cfg.DEFAULT_MEMBER_POSTING_ONLY
        self.host_name = mm_cfg.DEFAULT_HOST_NAME
        self.admin_member_chunksize = mm_cfg.DEFAULT_ADMIN_MEMBER_CHUNKSIZE
        self.administrivia = mm_cfg.DEFAULT_ADMINISTRIVIA
        self.preferred_language = mm_cfg.DEFAULT_SERVER_LANGUAGE
        self.available_languages = []
        # Analogs to these are initted in Digester.InitVars
        self.nondigestable = mm_cfg.DEFAULT_NONDIGESTABLE
        self.personalize = 0

	# BAW: This should really be set in SecurityManager.InitVars()
	self.password = crypted_password

        # Only one level of mixin inheritance allowed
        for baseclass in self.__class__.__bases__:
            if hasattr(baseclass, 'InitVars'):
                baseclass.InitVars(self)

        # These need to come near the bottom because they're dependent on
        # other settings.
        self.subject_prefix = mm_cfg.DEFAULT_SUBJECT_PREFIX % self.__dict__
        self.msg_header = mm_cfg.DEFAULT_MSG_HEADER
        self.msg_footer = mm_cfg.DEFAULT_MSG_FOOTER


    #
    # Web API support via administrative categories
    #
    def GetConfigCategories(self):
        class CategoryDict(UserDict):
            def __init__(self):
                UserDict.__init__(self)
                self.keysinorder = mm_cfg.ADMIN_CATEGORIES[:]
            def keys(self):
                return self.keysinorder
            def items(self):
                items = []
                for k in mm_cfg.ADMIN_CATEGORIES:
                    items.append((k, self.data[k]))
                return items
            def values(self):
                values = []
                for k in mm_cfg.ADMIN_CATEGORIES:
                    values.append(self.data[k])
                return values

        categories = CategoryDict()
        # Only one level of mixin inheritance allowed
        for gui in self._gui:
            k, v = gui.GetConfigCategory()
            categories[k] = (v, gui)
        return categories

    def GetConfigSubCategories(self, category):
        for gui in self._gui:
            if hasattr(gui, 'GetConfigSubCategories'):
                # Return the first one that knows about the given subcategory
                subcat = gui.GetConfigSubCategories(category)
                if subcat is not None:
                    return subcat
        return None

    def GetConfigInfo(self):
        info = {}
        for gui in self._gui:
            if hasattr(gui, 'GetConfigCategory') and \
                   hasattr(gui, 'GetConfigInfo'):
                key = gui.GetConfigCategory()[0]
                value = gui.GetConfigInfo(self)
                info[key] = value
        return info


    #
    # List creation
    #
    def Create(self, name, admin, crypted_password, langs=None):
        if Utils.list_exists(name):
            raise Errors.MMListAlreadyExistsError, name
        Utils.ValidateEmail(admin)
        omask = os.umask(0)
        try:
            try:
                os.makedirs(os.path.join(mm_cfg.LIST_DATA_DIR, name), 02775)
            except OSError:
                raise Errors.MMUnknownListError
        finally:
            os.umask(omask)
        self._full_path = os.path.join(mm_cfg.LIST_DATA_DIR, name)
        self._internal_name = name
        # Don't use Lock() since that tries to load the non-existant config.db
        self.__lock.lock()
        self.InitVars(name, admin, crypted_password)
        self.CheckValues()
        if langs is None:
            self.available_languages = [self.preferred_language]
        else:
            self.available_languages = langs
        self.Save()
        

    #
    # Database and filesystem I/O
    #
    def __save(self, dict):
        # Marshal this dictionary to file, and rotate the old version to a
        # backup file.  The dictionary must contain only builtin objects.  We
        # must guarantee that config.db is always valid so we never rotate
        # unless the we've successfully written the temp file.
        fname = os.path.join(self._full_path, 'config.db')
        fname_tmp = fname + '.tmp.%s.%d' % (socket.gethostname(), os.getpid())
        fname_last = fname + '.last'
        fp = None
        try:
            fp = open(fname_tmp, 'w')
            # marshal doesn't check for write() errors so this is safer.
            fp.write(marshal.dumps(dict))
            fp.close()
        except IOError, e:
            syslog('error',
                   'Failed config.db write, retaining old state.\n%s', e)
            if fp is not None:
                os.unlink(fname_tmp)
            raise
        # Now do config.db.tmp.xxx -> config.db -> config.db.last rotation
        # as safely as possible.
        try:
            # might not exist yet
            os.unlink(fname_last)
        except OSError, e:
            if e.errno <> errno.ENOENT: raise
        try:
            # might not exist yet
            os.link(fname, fname_last)
        except OSError, e:
            if e.errno <> errno.ENOENT: raise
        os.rename(fname_tmp, fname)

    def Save(self):
        # Refresh the lock, just to let other processes know we're still
        # interested in it.  This will raise a NotLockedError if we don't have
        # the lock (which is a serious problem!).  TBD: do we need to be more
        # defensive?
        self.__lock.refresh()
        # copy all public attributes to marshalable dictionary
        dict = {}
        for key, value in self.__dict__.items():
            if key[0] == '_' or type(value) is MethodType:
                continue
            dict[key] = value
        # Make config.db unreadable by `other', as it contains all the
        # list members' passwords (in clear text).
        omask = os.umask(007)
        try:
            self.__save(dict)
        finally:
            os.umask(omask)
            self.SaveRequestsDb()
        self.CheckHTMLArchiveDir()

    def __load(self, dbfile):
        # Attempt to load and unmarshal the specified database file, which
        # could be config.db or config.db.last.  On success return a 2-tuple
        # of (dictionary, None).  On error, return a 2-tuple of the form
        # (None, errorobj).
        try:
            fp = open(dbfile)
        except IOError, e:
            if e.errno <> errno.ENOENT: raise
            return None, e
        try:
            try:
                dict = marshal.load(fp)
                if type(dict) <> DictType:
                    return None, 'Unmarshal expected to return a dictionary'
            except (EOFError, ValueError, TypeError, MemoryError), e:
                return None, e
        finally:
            fp.close()
        return dict, None

    def Load(self, check_version=1):
        if not Utils.list_exists(self.internal_name()):
            raise Errors.MMUnknownListError
        # We first try to load config.db, which contains the up-to-date
        # version of the database.  If that fails, perhaps because it is
        # corrupted or missing, then we load config.db.last as a fallback.
        dbfile = os.path.join(self._full_path, 'config.db')
        lastfile = dbfile + '.last'
        dict, e = self.__load(dbfile)
        if dict is None:
            # Had problems with config.db.  Either it's missing or it's
            # corrupted.  Try config.db.last as a fallback.
            syslog('error', '%s db file was corrupt, using fallback: %s',
                   self.internal_name(), lastfile)
            dict, e = self.__load(lastfile)
            if dict is None:
                # config.db.last is busted too.  Nothing much we can do now.
                syslog('error', '%s fallback was corrupt, giving up',
                       self.internal_name())
                raise Errors.MMCorruptListDatabaseError, e
            # We had to read config.db.last, so copy it back to config.db.
            # This allows the logic in Save() to remain unchanged.  Ignore
            # any OSError resulting from possibly illegal (but unnecessary)
            # chmod.
            try:
                shutil.copy(lastfile, dbfile)
            except OSError, e:
                if e.errno <> errno.EPERM:
                    raise
        # Copy the unmarshaled dictionary into the attributes of the mailing
        # list object.
        self.__dict__.update(dict)
        if check_version:
            self.CheckValues()
            self.CheckVersion(dict)


    #
    # Sanity checks
    #
    def CheckVersion(self, stored_state):
        """Migrate prior version's state to new structure, if changed."""
        if (self.data_version >= mm_cfg.DATA_FILE_VERSION and 
                type(self.data_version) == type(mm_cfg.DATA_FILE_VERSION)):
            return
        else:
            self.InitVars() # Init any new variables, 
            self.Load(check_version = 0) # then reload the file
            from versions import Update
            Update(self, stored_state)
            self.data_version = mm_cfg.DATA_FILE_VERSION
        if self.Locked():
            self.Save()

    def CheckValues(self):
        """Normalize selected values to known formats."""
        if '' in urlparse(self.web_page_url)[:2]:
            # Either the "scheme" or the "network location" part of the parsed
            # URL is empty; substitute faulty value with (hopefully sane)
            # default.
            self.web_page_url = mm_cfg.DEFAULT_URL
        if self.web_page_url and self.web_page_url[-1] <> '/':
            self.web_page_url = self.web_page_url + '/'


    #
    # Membership management front-ends and assertion checks
    #
    def AddMember(self, userdesc, remote=None):
        """Front end to member subscription.

        This method enforces subscription policy, validates values, sends
        notifications, and any other grunt work involved in subscribing a
        user.  It eventually calls ApprovedAddMember() to do the actual work
        of subscribing the user.

        userdesc is an instance with the following public attributes:

            address  -- the unvalidated email address of the member
            fullname -- the member's full name (i.e. John Smith)
            digest   -- a flag indicating whether the user wants digests or not
            language -- the requested default language for the user
            password -- the user's password

        Other attributes may be defined later.  Only address is required; the
        others all have defaults (fullname='', digests=0, language=list's
        preferred language, password=generated).

        remote is a string which describes where this add request came from.
        """
        assert self.Locked()
        # Suck values out of userdesc, apply defaults, and reset the userdesc
        # attributes (for passing on to ApprovedAddMember()).  Lowercase the
        # addr's domain part.
        email = Utils.LCDomain(userdesc.address)
        name = getattr(userdesc, 'fullname', '')
        lang = getattr(userdesc, 'language', self.preferred_language)
        digest = getattr(userdesc, 'digest', None)
        password = getattr(userdesc, 'password', Utils.MakeRandomPassword())
        if digest is None:
            if self.nondigestable:
                digest = 0
            else:
                digest = 1
        # Validate the e-mail address to some degree.
        Utils.ValidateEmail(email)
        if self.isMember(email):
            raise Errors.MMAlreadyAMember
        if email.lower() == self.GetListEmail().lower():
            # Trying to subscribe the list to itself!
            raise Errors.MMBadEmailError

        # Sanity check the digest flag
        if digest and not self.digestable:
            raise Errors.MMCantDigestError
        elif not digest and not self.nondigestable:
            raise Errors.MMMustDigestError

        userdesc.address = email
        userdesc.fullname = name
        userdesc.digest = digest
        userdesc.language = lang
        userdesc.password = password

        # Apply the list's subscription policy.  0 means open subscriptions; 1
        # means the user must confirm; 2 means the admin must approve; 3 means
        # the user must confirm and then the admin must approve
        if self.subscribe_policy == 0:
            self.ApprovedAddMember(userdesc)
        elif self.subscribe_policy == 1 or self.subscribe_policy == 3:
            # User confirmation required.  BAW: this should probably just
            # accept a userdesc instance.
            cookie = Pending.new(Pending.SUBSCRIPTION,
                                 email, name, password, digest, lang)
            # Send the user the confirmation mailback
            if remote is None:
                by = remote = ''
            else:
                by = ' ' + remote
                remote = _(' from %(remote)s')

            recipient = self.GetMemberAdminEmail(email)
            realname = self.real_name
            confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                    cookie)
            text = Utils.maketext(
                'verify.txt',
                {'email'       : email,
                 'listaddr'    : self.GetListEmail(),
                 'listname'    : realname,
                 'cookie'      : cookie,
                 'requestaddr' : self.GetRequestEmail(),
                 'remote'      : remote,
                 'listadmin'   : self.GetAdminEmail(),
                 'confirmurl'  : confirmurl,
                 }, lang=lang, mlist=self)
            msg = Message.UserNotification(
                recipient, self.GetRequestEmail(),
                _('confirm %(cookie)s'),
                text)
            msg['Reply-To'] = self.GetRequestEmail()
            msg.send(self)
            if recipient <> email:
                who = "%s (%s)" % (email, recipient.split('@')[0])
            else:
                who = name
            syslog('subscribe', '%s: pending %s %s',
                   self.internal_name(), who, by)
            raise Errors.MMSubscribeNeedsConfirmation
        else:
            # Subscription approval is required.  Add this entry to the admin
            # requests database.  BAW: this should probably take a userdesc
            # just like above.
            self.HoldSubscription(email, fullname, password, digest, lang)
            raise Errors.MMNeedApproval, _(
                'subscriptions to %(realname)s require administrator approval')

    def ApprovedAddMember(self, userdesc, ack=None, admin_notif=None):
        """Add a member right now.

        The member's subscription must be approved by what ever policy the
        list enforces.

        userdesc is as above in AddMember().

        ack is a flag that specifies whether the user should get an
        acknowledgement of their being subscribed.  Default is to use the
        list's default flag value.

        admin_notif is a flag that specifies whether the list owner should get
        an acknowledgement of this subscription.  Default is to use the list's
        default flag value.
        """
        assert self.Locked()
        # Set up default flag values
        if ack is None:
            ack = self.send_welcome_msg
        if admin_notif is None:
            admin_notif = self.admin_notify_mchanges

        # Suck values out of userdesc, and apply defaults.
        email = Utils.LCDomain(userdesc.address)
        name = getattr(userdesc, 'fullname', '')
        lang = getattr(userdesc, 'language', self.preferred_language)
        digest = getattr(userdesc, 'digest', None)
        password = getattr(userdesc, 'password', Utils.MakeRandomPassword())
        if digest is None:
            if self.nondigestable:
                digest = 0
            else:
                digest = 1

        # Let's be extra cautious
        Utils.ValidateEmail(email)
        if self.isMember(email):
            raise Errors.MMAlreadyAMember, email

        self.addNewMember(email, realname=name, digest=digest,
                          password=password, language=lang)
        self.setMemberOption(email, mm_cfg.DisableMime,
                             1 - self.mime_is_default_digest)

        # Now send and log results
        if digest:
            kind = ' (digest)'
        else:
            kind = ''

        syslog('subscribe', '%s: new%s %s (%s)', self.internal_name(),
               kind, email, name)

        if ack:
            self.SendSubscribeAck(email, self.getMemberPassword(email), digest)
        if admin_notif:
            adminaddr = self.GetAdminEmail()
            realname = self.real_name
            subject = _('%(realname)s subscription notification')
            text = Utils.maketext(
                "adminsubscribeack.txt",
                {"listname" : self.real_name,
                 "member"   : dump_address_pair((name, email)),
                 }, lang=lang, mlist=self)
            msg = Message.UserNotification(
                self.owner, Utils.get_site_email(self.host_name, '-admin'),
                subject, text)
            msg.send(self)

    def ApprovedDeleteMember(self, name, whence=None,
                             admin_notif=None, userack=1):
        if admin_notif is None:
            admin_notif = self.admin_notify_mchanges

        # Delete a member, for which we know the approval has been made
        fullname, emailaddr = parseaddr(name)
        if not self.isMember(emailaddr):
            raise Errors.MMNoSuchUserError
        # Remove the member
        self.removeMember(emailaddr)
        # And send an acknowledgement to the user...
        if userack and self.goodbye_msg and len(self.goodbye_msg):
            self.SendUnsubscribeAck(name)
        # ...and to the administrator
        if admin_notif:
            realname = self.real_name
            subject = _('%(realname)s unsubscribe notification')
            text = Utils.maketext(
                'adminunsubscribeack.txt',
                {'member'  : name,
                 'listname': self.real_name,
                 }, mlist=self)
            msg = Message.UserNotification(
                self.owner, Utils.get_site_email(self.host_name, '-admin'),
                subject, text)
            msg.send(self)
        if whence:
            whence = "; %s" % whence
        else:
            whence = ""
        syslog('subscribe', '%s: deleted %s%s',
               self.internal_name(), name, whence)

    def ChangeMemberName(self, addr, name, globally):
        self.setMemberName(addr, name)
        if not globally:
            return
        for listname in Utils.list_names():
            # Don't bother with ourselves
            if listname == self.internal_name():
                continue
            mlist = MailList(listname, lock=0)
            if mlist.host_name <> self.host_name:
                continue
            if not mlist.isMember(oldaddr):
                continue
            mlist.Lock()
            try:
                mlist.setMemberName(addr, name)
                mlist.Save()
            finally:
                mlist.Unlock()

    def ChangeMemberAddress(self, oldaddr, newaddr, globally):
        # Changing a member address consists of verifying the new address,
        # making sure the new address isn't already a member, and optionally
        # going through the confirmation process.
        #
        # Most of these checks are copied from AddMember
        newaddr = Utils.LCDomain(newaddr)
        Utils.ValidateEmail(newaddr)
        # Raise an exception if this email address is already a member of the
        # list, but only if the new address is the same case-wise as the old
        # address.
        if newaddr == oldaddr and self.isMember(newaddr):
            raise Errors.MMAlreadyAMember
        if newaddr == self.GetListEmail().lower():
            raise Errors.MMBadEmailError
        # Pend the subscription change
        cookie = Pending.new(Pending.CHANGE_OF_ADDRESS,
                             oldaddr, newaddr, globally)
        confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                cookie)
        realname = self.real_name
        text = Utils.maketext(
            'verify.txt',
            {'email'      : newaddr,
             'listaddr'   : self.GetListEmail(),
             'listname'   : realname,
             'cookie'     : cookie,
             'requestaddr': self.GetRequestEmail(),
             'remote'     : '',
             'listadmin'  : self.GetAdminEmail(),
             'confirmurl' : confirmurl,
             }, lang=self.getMemberLanguage(oldaddr), mlist=self)
        msg = Message.UserNotification(
            newaddr, self.GetRequestEmail(),
            _('confirm %(cookie)s'),
            text)
        msg['Reply-To'] = self.GetRequestEmail()
        msg.send(self)

    def ApprovedChangeMemberAddress(self, oldaddr, newaddr, globally):
        # Change the membership for the current list first.  We don't lock and
        # save ourself since we assume that the list is already locked.
        self.changeMemberAddress(oldaddr, newaddr)
        # If globally is true, then we also include every list for which
        # oldaddr is a member.
        if not globally:
            return
        for listname in Utils.list_names():
            # Don't bother with ourselves
            if listname == self.internal_name():
                continue
            mlist = MailList(listname, lock=0)
            if mlist.host_name <> self.host_name:
                continue
            if not mlist.isMember(oldaddr) or mlist.isMember(newaddr):
                continue
            mlist.Lock()
            try:
                mlist.changeMemberAddress(oldaddr, newaddr)
                mlist.Save()
            finally:
                mlist.Unlock()


    #
    # Confirmation processing
    #
    def ProcessConfirmation(self, cookie, userdesc_overrides=None):
        data = Pending.confirm(cookie)
        if data is None:
            raise Errors.MMBadConfirmation, 'data is None'
        try:
            op = data[0]
            data = data[1:]
        except ValueError:
            raise Errors.MMBadConfirmation, 'op-less data %s' % (data,)
        if op == Pending.SUBSCRIPTION:
            try:
                addr, fullname, password, digest, lang = data
            except ValueError:
                raise Errors.MMBadConfirmation, 'bad subscr data %s' % (data,)
            if self.subscribe_policy == 3: # confirm + approve
                self.HoldSubscription(addr, fullname, password, digest, lang)
                name = self.real_name
                raise Errors.MMNeedApproval, _(
                    'subscriptions to %(name)s require administrator approval')
            userdesc = UserDesc(addr, fullname, password, digest, lang)
            if userdesc_overrides is not None:
                userdesc += userdesc_overrides
            self.ApprovedAddMember(userdesc)
            return op, addr, password, digest, lang
        elif op == Pending.UNSUBSCRIPTION:
            addr = data[0]
            # Can raise MMNoSuchUserError if they unsub'd via other means
            self.ApprovedDeleteMember(addr, whence='web confirmation')
            return op, addr
        elif op == Pending.CHANGE_OF_ADDRESS:
            oldaddr, newaddr, globally = data
            self.ApprovedChangeMemberAddress(oldaddr, newaddr, globally)
            return op, oldaddr, newaddr

    def ConfirmUnsubscription(self, addr, lang=None, remote=None):
        if lang is None:
            lang = self.getMemberLanguage(addr)
        cookie = Pending.new(Pending.UNSUBSCRIPTION, addr)
        confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                cookie)
        realname = self.real_name
        if remote is not None:
            by = " " + remote
            remote = _(" from %(remote)s")
        else:
            by = ""
            remote = ""
        text = Utils.maketext(
            'unsub.txt',
            {'email'       : addr,
             'listaddr'    : self.GetListEmail(),
             'listname'    : realname,
             'cookie'      : cookie,
             'requestaddr' : self.GetRequestEmail(),
             'remote'      : remote,
             'listadmin'   : self.GetAdminEmail(),
             'confirmurl'  : confirmurl,
             }, lang=lang, mlist=self)
        msg = Message.UserNotification(
            addr, self.GetRequestEmail(),
            _('confirm %(cookie)s'),
            text)
        msg['Reply-To'] = self.GetRequestEmail()
        msg.send(self)


    #
    # Miscellaneous stuff
    #
    def HasExplicitDest(self, msg):
        """True if list name or any acceptable_alias is included among the
        to or cc addrs."""
        # BAW: fall back to Utils.ParseAddr if the first test fails.
        # this is the list's full address
        listfullname = '%s@%s' % (self.internal_name(), self.host_name)
        recips = []
        # check all recipient addresses against the list's explicit addresses,
        # specifically To: Cc: and Resent-to:
        to = []
        for header in ('to', 'cc', 'resent-to', 'resent-cc'):
            to.extend(getaddresses(msg.getall(header)))
        for fullname, addr in to:
            # It's possible that if the header doesn't have a valid
            # (i.e. RFC822) value, we'll get None for the address.  So skip
            # it.
            if addr is None:
                continue
            addr = addr.lower()
            localpart = addr.split('@')[0]
            if (# TBD: backwards compatibility: deprecated
                    localpart == self.internal_name() or
                    # exact match against the complete list address
                    addr == listfullname):
                return 1
            recips.append((addr, localpart))
        #
        # helper function used to match a pattern against an address.  Do it
        def domatch(pattern, addr):
            try:
                if re.match(pattern, addr):
                    return 1
            except re.error:
                # The pattern is a malformed regexp -- try matching safely,
                # with all non-alphanumerics backslashed:
                if re.match(re.escape(pattern), addr):
                    return 1
        #
        # Here's the current algorithm for matching acceptable_aliases:
        #
        # 1. If the pattern does not have an `@' in it, we first try matching
        #    it against just the localpart.  This was the behavior prior to
        #    2.0beta3, and is kept for backwards compatibility.
        #    (deprecated).
        #
        # 2. If that match fails, or the pattern does have an `@' in it, we
        #    try matching against the entire recip address.
        for addr, localpart in recips:
            for alias in self.acceptable_aliases.split('\n'):
                stripped = alias.strip()
                if not stripped:
                    # ignore blank or empty lines
                    continue
                if '@' not in stripped and domatch(stripped, localpart):
                    return 1
                if domatch(stripped, addr):
                    return 1
        return 0

    def parse_matching_header_opt(self):
        """Return a list of triples [(field name, regex, line), ...]."""
        # - Blank lines and lines with '#' as first char are skipped.
        # - Leading whitespace in the matchexp is trimmed - you can defeat
        #   that by, eg, containing it in gratuitous square brackets.
        all = []
        for line in self.bounce_matching_headers.split('\n'):
            line = line.strip()
            # Skip blank lines and lines *starting* with a '#'.
            if not line or line[0] == "#":
                continue
            i = line.find(':')
            if i < 0:
                # This didn't look like a header line.  BAW: should do a
                # better job of informing the list admin.
                syslog('config', 'bad bounce_matching_header line: %s\n%s',
                       self.real_name, line)
            else:
                header = line[:i]
                value = line[i+1:].lstrip()
                try:
                    cre = re.compile(value, re.IGNORECASE)
                except re.error, e:
                    # The regexp was malformed.  BAW: should do a better
                    # job of informing the list admin.
                    syslog('config', '''\
bad regexp in bounce_matching_header line: %s
\n%s (cause: %s)''', self.real_name, value, e)
                else:
                    all.append((header, cre, line))
        return all

    def hasMatchingHeader(self, msg):
        """Return true if named header field matches a regexp in the
        bounce_matching_header list variable.

        Returns constraint line which matches or empty string for no
        matches.
        """
        for header, cre, line in self.parse_matching_header_opt():
            for value in msg.getall(header):
                if cre.search(value):
                    return line
        return 0


    #
    # Multilingual (i18n) support
    #
    def GetAvailableLanguages(self):
        langs = self.available_languages
        # If we don't add this, and the site admin has never added any
        # language support to the list, then the general admin page may have a
        # blank field where the list owner is supposed to chose the list's
        # preferred language.
        if mm_cfg.DEFAULT_SERVER_LANGUAGE not in langs:
            langs.append(mm_cfg.DEFAULT_SERVER_LANGUAGE)
        return langs
