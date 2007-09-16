# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.


"""The class representing a Mailman mailing list.

Mixes in many task-specific classes.
"""

import os
import re
import sys
import time
import errno
import shutil
import socket
import urllib
import cPickle
import logging
import marshal
import email.Iterators

from UserDict import UserDict
from cStringIO import StringIO
from string import Template
from types import MethodType
from urlparse import urlparse
from zope.interface import implements

from email.Header import Header
from email.Utils import getaddresses, formataddr, parseaddr

from Mailman import Errors
from Mailman import LockFile
from Mailman import Utils
from Mailman import Version
from Mailman import database
from Mailman.UserDesc import UserDesc
from Mailman.configuration import config
from Mailman.interfaces import *

# Base classes
from Mailman.Archiver import Archiver
from Mailman.Bouncer import Bouncer
from Mailman.Deliverer import Deliverer
from Mailman.Digester import Digester
from Mailman.HTMLFormatter import HTMLFormatter
from Mailman.SecurityManager import SecurityManager

# GUI components package
from Mailman import Gui

# Other useful classes
from Mailman import i18n
from Mailman import MemberAdaptor
from Mailman import Message

_ = i18n._

DOT         = '.'
EMPTYSTRING = ''
OR = '|'

clog    = logging.getLogger('mailman.config')
elog    = logging.getLogger('mailman.error')
vlog    = logging.getLogger('mailman.vette')
slog    = logging.getLogger('mailman.subscribe')



# Use mixins here just to avoid having any one chunk be too large.
class MailList(object, HTMLFormatter, Deliverer,
               Archiver, Digester, SecurityManager, Bouncer):

    implements(
        IMailingList,
        IMailingListAddresses,
        IMailingListIdentity,
        IMailingListRosters,
        )

    def __init__(self, data):
        self._data = data
        # Only one level of mixin inheritance allowed
        for baseclass in self.__class__.__bases__:
            if hasattr(baseclass, '__init__'):
                baseclass.__init__(self)
        # Initialize volatile attributes
        self.InitTempVars()
        # Give the extension mechanism a chance to process this list.
        try:
            from Mailman.ext import init_mlist
        except ImportError:
            pass
        else:
            init_mlist(self)

    def __getattr__(self, name):
        missing = object()
        if name.startswith('_'):
            return super(MailList, self).__getattr__(name)
        # Delegate to the database model object if it has the attribute.
        obj = getattr(self._data, name, missing)
        if obj is not missing:
            return obj
        # Delegate to the member adapter next.
        obj = getattr(self._memberadaptor, name, missing)
        if obj is not missing:
            return obj
        # Finally, delegate to one of the gui components.
        for guicomponent in self._gui:
            obj = getattr(guicomponent, name, missing)
            if obj is not missing:
                return obj
        # Nothing left to delegate to, so it's got to be an error.
        raise AttributeError(name)

    def __repr__(self):
        if self.Locked():
            status = '(locked)'
        else:
            status = '(unlocked)'
        return '<mailing list "%s" %s at %x>' % (
            self.fqdn_listname, status, id(self))


    #
    # Lock management
    #
    def _make_lock(self, name, lock=False):
        self._lock = LockFile.LockFile(
            os.path.join(config.LOCK_DIR, name) + '.lock',
            lifetime=config.LIST_LOCK_LIFETIME)
        if lock:
            self._lock.lock()

    def Lock(self, timeout=0):
        self._lock.lock(timeout)
        self._memberadaptor.lock()
        # Must reload our database for consistency.  Watch out for lists that
        # don't exist.
        try:
            self.Load()
        except Exception:
            self.Unlock()
            raise

    def Unlock(self):
        self._lock.unlock(unconditionally=True)
        self._memberadaptor.unlock()

    def Locked(self):
        return self._lock.locked()



    #
    # Useful accessors
    #
    @property
    def full_path(self):
        return self._full_path



    # IMailingListAddresses

    @property
    def posting_address(self):
        return self.fqdn_listname

    @property
    def noreply_address(self):
        return '%s@%s' % (config.NO_REPLY_ADDRESS, self.host_name)

    @property
    def owner_address(self):
        return '%s-owner@%s' % (self.list_name, self.host_name)

    @property
    def request_address(self):
        return '%s-request@%s' % (self.list_name, self.host_name)

    @property
    def bounces_address(self):
        return '%s-bounces@%s' % (self.list_name, self.host_name)

    @property
    def join_address(self):
        return '%s-join@%s' % (self.list_name, self.host_name)

    @property
    def leave_address(self):
        return '%s-leave@%s' % (self.list_name, self.host_name)

    @property
    def subscribe_address(self):
        return '%s-subscribe@%s' % (self.list_name, self.host_name)

    @property
    def unsubscribe_address(self):
        return '%s-unsubscribe@%s' % (self.list_name, self.host_name)

    def confirm_address(self, cookie):
        local_part = Template(config.VERP_CONFIRM_FORMAT).safe_substitute(
            address = '%s-confirm' % self.list_name,
            cookie  = cookie)
        return '%s@%s' % (local_part, self.host_name)

    def GetConfirmJoinSubject(self, listname, cookie):
        if config.VERP_CONFIRMATIONS and cookie:
            cset = i18n.get_translation().charset() or \
                       Utils.GetCharSet(self.preferred_language)
            subj = Header(
     _('Your confirmation is required to join the %(listname)s mailing list'),
                          cset, header_name='subject')
            return subj
        else:
            return 'confirm ' + cookie

    def GetConfirmLeaveSubject(self, listname, cookie):
        if config.VERP_CONFIRMATIONS and cookie:
            cset = i18n.get_translation().charset() or \
                       Utils.GetCharSet(self.preferred_language)
            subj = Header(
     _('Your confirmation is required to leave the %(listname)s mailing list'),
                          cset, header_name='subject')
            return subj
        else:
            return 'confirm ' + cookie

    def GetListEmail(self):
        return self.getListAddress()

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

    def GetScriptURL(self, target, absolute=False):
        if absolute:
            return self.web_page_url + target + '/' + self.fqdn_listname
        else:
            return Utils.ScriptURL(target) + '/' + self.fqdn_listname

    def GetOptionsURL(self, user, obscure=False, absolute=False):
        url = self.GetScriptURL('options', absolute)
        if obscure:
            user = Utils.ObscureEmail(user)
        return '%s/%s' % (url, urllib.quote(user.lower()))


    #
    # Instance and subcomponent initialization
    #
    def InitTempVars(self):
        """Set transient variables of this and inherited classes."""
        # Because of the semantics of the database layer, it's possible that
        # this method gets called more than once on an existing object.  For
        # example, if the MailList object is expunged from the current db
        # session, then this may get called again when the object's persistent
        # attributes are re-read from the database.  This can have nasty
        # consequences, so ensure that we're only called once.
        if hasattr(self, '_lock'):
            return
        # Attach a membership adaptor instance.
        parts = config.MEMBER_ADAPTOR_CLASS.split(DOT)
        adaptor_class = parts.pop()
        adaptor_module = DOT.join(parts)
        __import__(adaptor_module)
        mod = sys.modules[adaptor_module]
        self._memberadaptor = getattr(mod, adaptor_class)(self)
        self._make_lock(self.fqdn_listname)
        # Create the list's data directory.
        self._full_path = os.path.join(config.LIST_DATA_DIR, self.fqdn_listname)
        Utils.makedirs(self._full_path)
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


    #
    # Web API support via administrative categories
    #
    def GetConfigCategories(self):
        class CategoryDict(UserDict):
            def __init__(self):
                UserDict.__init__(self)
                self.keysinorder = config.ADMIN_CATEGORIES[:]
            def keys(self):
                return self.keysinorder
            def items(self):
                items = []
                for k in config.ADMIN_CATEGORIES:
                    items.append((k, self.data[k]))
                return items
            def values(self):
                values = []
                for k in config.ADMIN_CATEGORIES:
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

    def GetConfigInfo(self, category, subcat=None):
        for gui in self._gui:
            if hasattr(gui, 'GetConfigInfo'):
                value = gui.GetConfigInfo(self, category, subcat)
                if value:
                    return value


    def Save(self):
        # Refresh the lock, just to let other processes know we're still
        # interested in it.  This will raise a NotLockedError if we don't have
        # the lock (which is a serious problem!).  TBD: do we need to be more
        # defensive?
        self._lock.refresh()
        # The member adaptor may have its own save operation
        self._memberadaptor.save()
        self.CheckHTMLArchiveDir()

    def Load(self):
        self._memberadaptor.load()



    #
    # Sanity checks
    #
    def CheckVersion(self, stored_state):
        """Auto-update schema if necessary."""
        if self.data_version >= Version.DATA_FILE_VERSION:
            return
        # Then reload the database (but don't recurse).  Force a reload even
        # if we have the most up-to-date state.
        self.Load(self.fqdn_listname, check_version=False)
        # We must hold the list lock in order to update the schema
        waslocked = self.Locked()
        if not waslocked:
            self.Lock()
        try:
            from versions import Update
            Update(self, stored_state)
            self.data_version = Version.DATA_FILE_VERSION
            self.Save()
        finally:
            if not waslocked:
                self.Unlock()

    def CheckValues(self):
        """Normalize selected values to known formats."""
        if '' in urlparse(self.web_page_url)[:2]:
            # Either the "scheme" or the "network location" part of the parsed
            # URL is empty; substitute faulty value with (hopefully sane)
            # default.  Note that DEFAULT_URL is obsolete.
            self.web_page_url = (
                config.DEFAULT_URL or
                config.DEFAULT_URL_PATTERN % config.DEFAULT_URL_HOST)
        if self.web_page_url and self.web_page_url[-1] <> '/':
            self.web_page_url = self.web_page_url + '/'
        # Legacy reply_to_address could be an illegal value.  We now verify
        # upon setting and don't check it at the point of use.
        try:
            if self.reply_to_address.strip() and self.reply_goes_to_list:
                Utils.ValidateEmail(self.reply_to_address)
        except Errors.EmailAddressError:
            elog.error('Bad reply_to_address "%s" cleared for list: %s',
                       self.reply_to_address, self.internal_name())
            self.reply_to_address = ''
            self.reply_goes_to_list = 0
        # Legacy topics may have bad regular expressions in their patterns
        goodtopics = []
        for name, pattern, desc, emptyflag in self.topics:
            try:
                orpattern = OR.join(pattern.splitlines())
                re.compile(orpattern)
            except (re.error, TypeError):
                elog.error('Bad topic pattern "%s" for list: %s',
                           orpattern, self.internal_name())
            else:
                goodtopics.append((name, pattern, desc, emptyflag))
        self.topics = goodtopics


    #
    # Membership management front-ends and assertion checks
    #
    def InviteNewMember(self, userdesc, text=''):
        """Invite a new member to the list.

        This is done by creating a subscription pending for the user, and then
        crafting a message to the member informing them of the invitation.
        """
        invitee = userdesc.address
        Utils.ValidateEmail(invitee)
        # check for banned address
        pattern = self.GetBannedPattern(invitee)
        if pattern:
            raise Errors.MembershipIsBanned, pattern
        # Hack alert!  Squirrel away a flag that only invitations have, so
        # that we can do something slightly different when an invitation
        # subscription is confirmed.  In those cases, we don't need further
        # admin approval, even if the list is so configured.  The flag is the
        # list name to prevent invitees from cross-subscribing.
        userdesc.invitation = self.internal_name()
        cookie = self.pend_new(Pending.SUBSCRIPTION, userdesc)
        requestaddr = self.getListAddress('request')
        confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                cookie)
        listname = self.real_name
        text += Utils.maketext(
            'invite.txt',
            {'email'      : invitee,
             'listname'   : listname,
             'hostname'   : self.host_name,
             'confirmurl' : confirmurl,
             'requestaddr': requestaddr,
             'cookie'     : cookie,
             'listowner'  : self.GetOwnerEmail(),
             }, mlist=self)
        sender = self.GetRequestEmail(cookie)
        msg = Message.UserNotification(
            invitee, sender,
            text=text, lang=self.preferred_language)
        subj = self.GetConfirmJoinSubject(listname, cookie)
        del msg['subject']
        msg['Subject'] = subj
        msg.send(self)

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
            raise Errors.MMAlreadyAMember, email
        if email.lower() == self.GetListEmail().lower():
            # Trying to subscribe the list to itself!
            raise Errors.InvalidEmailAddress
        realname = self.real_name
        # Is the subscribing address banned from this list?
        pattern = self.GetBannedPattern(email)
        if pattern:
            vlog.error('%s banned subscription: %s (matched: %s)',
                       realname, email, pattern)
            raise Errors.MembershipIsBanned, pattern
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
            self.ApprovedAddMember(userdesc, whence=remote or '')
        elif self.subscribe_policy == 1 or self.subscribe_policy == 3:
            # User confirmation required.  BAW: this should probably just
            # accept a userdesc instance.
            cookie = self.pend_new(Pending.SUBSCRIPTION, userdesc)
            # Send the user the confirmation mailback
            if remote is None:
                by = remote = ''
            else:
                by = ' ' + remote
                remote = _(' from %(remote)s')

            recipient = self.GetMemberAdminEmail(email)
            confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                    cookie)
            text = Utils.maketext(
                'verify.txt',
                {'email'       : email,
                 'listaddr'    : self.GetListEmail(),
                 'listname'    : realname,
                 'cookie'      : cookie,
                 'requestaddr' : self.getListAddress('request'),
                 'remote'      : remote,
                 'listadmin'   : self.GetOwnerEmail(),
                 'confirmurl'  : confirmurl,
                 }, lang=lang, mlist=self)
            msg = Message.UserNotification(
                recipient, self.GetRequestEmail(cookie),
                text=text, lang=lang)
            # BAW: See ChangeMemberAddress() for why we do it this way...
            del msg['subject']
            msg['Subject'] = self.GetConfirmJoinSubject(realname, cookie)
            msg['Reply-To'] = self.GetRequestEmail(cookie)
            msg.send(self)
            who = formataddr((name, email))
            slog.info('%s: pending %s %s', self.internal_name(), who, by)
            raise Errors.MMSubscribeNeedsConfirmation
        elif self.HasAutoApprovedSender(email):
            # no approval necessary:
            self.ApprovedAddMember(userdesc)
        else:
            # Subscription approval is required.  Add this entry to the admin
            # requests database.  BAW: this should probably take a userdesc
            # just like above.
            self.HoldSubscription(email, name, password, digest, lang)
            raise Errors.MMNeedApproval, _(
                'subscriptions to %(realname)s require moderator approval')

    def DeleteMember(self, name, whence=None, admin_notif=None, userack=True):
        realname, email = parseaddr(name)
        if self.unsubscribe_policy == 0:
            self.ApprovedDeleteMember(name, whence, admin_notif, userack)
        else:
            self.HoldUnsubscription(email)
            raise Errors.MMNeedApproval, _(
                'unsubscriptions require moderator approval')

    def ApprovedDeleteMember(self, name, whence=None,
                             admin_notif=None, userack=None):
        if userack is None:
            userack = self.send_goodbye_msg
        if admin_notif is None:
            admin_notif = self.admin_notify_mchanges
        # Delete a member, for which we know the approval has been made
        fullname, emailaddr = parseaddr(name)
        userlang = self.getMemberLanguage(emailaddr)
        # Remove the member
        self.removeMember(emailaddr)
        # And send an acknowledgement to the user...
        if userack:
            self.SendUnsubscribeAck(emailaddr, userlang)
        # ...and to the administrator
        if admin_notif:
            realname = self.real_name
            subject = _('%(realname)s unsubscribe notification')
            text = Utils.maketext(
                'adminunsubscribeack.txt',
                {'member'  : name,
                 'listname': self.real_name,
                 }, mlist=self)
            msg = Message.OwnerNotification(self, subject, text)
            msg.send(self)
        if whence:
            whence = "; %s" % whence
        else:
            whence = ""
        slog.info('%s: deleted %s%s', self.internal_name(), name, whence)

    def ChangeMemberName(self, addr, name, globally):
        self.setMemberName(addr, name)
        if not globally:
            return
        for listname in config.list_manager.names:
            # Don't bother with ourselves
            if listname == self.internal_name():
                continue
            mlist = MailList(listname, lock=0)
            if mlist.host_name <> self.host_name:
                continue
            if not mlist.isMember(addr):
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
        # address and we're not doing a global change.
        if not globally and newaddr == oldaddr and self.isMember(newaddr):
            raise Errors.MMAlreadyAMember
        if newaddr == self.GetListEmail().lower():
            raise Errors.InvalidEmailAddress
        realname = self.real_name
        # Don't allow changing to a banned address. MAS: maybe we should
        # unsubscribe the oldaddr too just for trying, but that's probably
        # too harsh.
        pattern = self.GetBannedPattern(newaddr)
        if pattern:
            vlog.error('%s banned address change: %s -> %s (matched: %s)',
                       realname, oldaddr, newaddr, pattern)
            raise Errors.MembershipIsBanned, pattern
        # Pend the subscription change
        cookie = self.pend_new(Pending.CHANGE_OF_ADDRESS,
                               oldaddr, newaddr, globally)
        confirmurl = '%s/%s' % (self.GetScriptURL('confirm', absolute=1),
                                cookie)
        lang = self.getMemberLanguage(oldaddr)
        text = Utils.maketext(
            'verify.txt',
            {'email'      : newaddr,
             'listaddr'   : self.GetListEmail(),
             'listname'   : realname,
             'cookie'     : cookie,
             'requestaddr': self.getListAddress('request'),
             'remote'     : '',
             'listadmin'  : self.GetOwnerEmail(),
             'confirmurl' : confirmurl,
             }, lang=lang, mlist=self)
        # BAW: We don't pass the Subject: into the UserNotification
        # constructor because it will encode it in the charset of the language
        # being used.  For non-us-ascii charsets, this means it will probably
        # quopri quote it, and thus replies will also be quopri encoded.  But
        # CommandRunner doesn't yet grok such headers.  So, just set the
        # Subject: in a separate step, although we have to delete the one
        # UserNotification adds.
        msg = Message.UserNotification(
            newaddr, self.GetRequestEmail(cookie),
            text=text, lang=lang)
        del msg['subject']
        msg['Subject'] = self.GetConfirmJoinSubject(realname, cookie)
        msg['Reply-To'] = self.GetRequestEmail(cookie)
        msg.send(self)

    def ApprovedChangeMemberAddress(self, oldaddr, newaddr, globally):
        # Check here for banned address in case address was banned after
        # confirmation was mailed. MAS: If it's global change should we just
        # skip this list and proceed to the others? For now we'll throw the
        # exception.
        pattern = self.GetBannedPattern(newaddr)
        if pattern:
            raise Errors.MembershipIsBanned, pattern
        # It's possible they were a member of this list, but choose to change
        # their membership globally.  In that case, we simply remove the old
        # address.
        if self.getMemberCPAddress(oldaddr) == newaddr:
            self.removeMember(oldaddr)
        else:
            self.changeMemberAddress(oldaddr, newaddr)
            self.log_and_notify_admin(oldaddr, newaddr)
        # If globally is true, then we also include every list for which
        # oldaddr is a member.
        if not globally:
            return
        for listname in config.list_manager.names:
            # Don't bother with ourselves
            if listname == self.internal_name():
                continue
            mlist = MailList(listname, lock=0)
            if mlist.host_name <> self.host_name:
                continue
            if not mlist.isMember(oldaddr):
                continue
            # If new address is banned from this list, just skip it.
            if mlist.GetBannedPattern(newaddr):
                continue
            mlist.Lock()
            try:
                # Same logic as above, re newaddr is already a member
                if mlist.getMemberCPAddress(oldaddr) == newaddr:
                    mlist.removeMember(oldaddr)
                else:
                    mlist.changeMemberAddress(oldaddr, newaddr)
                    mlist.log_and_notify_admin(oldaddr, newaddr)
                mlist.Save()
            finally:
                mlist.Unlock()

    def log_and_notify_admin(self, oldaddr, newaddr):
        """Log member address change and notify admin if requested."""
        slog.info('%s: changed member address from %s to %s',
                  self.internal_name(), oldaddr, newaddr)
        if self.admin_notify_mchanges:
            lang = self.preferred_language
            otrans = i18n.get_translation()
            i18n.set_language(lang)
            try:
                realname = self.real_name
                subject = _('%(realname)s address change notification')
            finally:
                i18n.set_translation(otrans)
            name = self.getMemberName(newaddr)
            if name is None:
                name = ''
            if isinstance(name, unicode):
                name = name.encode(Utils.GetCharSet(lang), 'replace')
            text = Utils.maketext(
                'adminaddrchgack.txt',
                {'name'    : name,
                 'oldaddr' : oldaddr,
                 'newaddr' : newaddr,
                 'listname': self.real_name,
                 }, mlist=self)
            msg = Message.OwnerNotification(self, subject, text)
            msg.send(self)


    #
    # Confirmation processing
    #
    def ProcessConfirmation(self, cookie, context=None):
        rec = self.pend_confirm(cookie)
        if rec is None:
            raise Errors.MMBadConfirmation, 'No cookie record for %s' % cookie
        try:
            op = rec[0]
            data = rec[1:]
        except ValueError:
            raise Errors.MMBadConfirmation, 'op-less data %s' % (rec,)
        if op == Pending.SUBSCRIPTION:
            whence = 'via email confirmation'
            try:
                userdesc = data[0]
                # If confirmation comes from the web, context should be a
                # UserDesc instance which contains overrides of the original
                # subscription information.  If it comes from email, then
                # context is a Message and isn't relevant, so ignore it.
                if isinstance(context, UserDesc):
                    userdesc += context
                    whence = 'via web confirmation'
                addr = userdesc.address
                fullname = userdesc.fullname
                password = userdesc.password
                digest = userdesc.digest
                lang = userdesc.language
            except ValueError:
                raise Errors.MMBadConfirmation, 'bad subscr data %s' % (data,)
            # Hack alert!  Was this a confirmation of an invitation?
            invitation = getattr(userdesc, 'invitation', False)
            # We check for both 2 (approval required) and 3 (confirm +
            # approval) because the policy could have been changed in the
            # middle of the confirmation dance.
            if invitation:
                if invitation <> self.internal_name():
                    # Not cool.  The invitee was trying to subscribe to a
                    # different list than they were invited to.  Alert both
                    # list administrators.
                    self.SendHostileSubscriptionNotice(invitation, addr)
                    raise Errors.HostileSubscriptionError
            elif self.subscribe_policy in (2, 3) and \
                    not self.HasAutoApprovedSender(addr):
                self.HoldSubscription(addr, fullname, password, digest, lang)
                name = self.real_name
                raise Errors.MMNeedApproval, _(
                    'subscriptions to %(name)s require administrator approval')
            self.ApprovedAddMember(userdesc, whence=whence)
            return op, addr, password, digest, lang
        elif op == Pending.UNSUBSCRIPTION:
            addr = data[0]
            # Log file messages don't need to be i18n'd
            if isinstance(context, Message.Message):
                whence = 'email confirmation'
            else:
                whence = 'web confirmation'
            # Can raise NotAMemberError if they unsub'd via other means
            self.ApprovedDeleteMember(addr, whence=whence)
            return op, addr
        elif op == Pending.CHANGE_OF_ADDRESS:
            oldaddr, newaddr, globally = data
            self.ApprovedChangeMemberAddress(oldaddr, newaddr, globally)
            return op, oldaddr, newaddr
        elif op == Pending.HELD_MESSAGE:
            id = data[0]
            approved = None
            # Confirmation should be coming from email, where context should
            # be the confirming message.  If the message does not have an
            # Approved: header, this is a discard.  If it has an Approved:
            # header that does not match the list password, then we'll notify
            # the list administrator that they used the wrong password.
            # Otherwise it's an approval.
            if isinstance(context, Message.Message):
                # See if it's got an Approved: header, either in the headers,
                # or in the first text/plain section of the response.  For
                # robustness, we'll accept Approve: as well.
                approved = context.get('Approved', context.get('Approve'))
                if not approved:
                    try:
                        subpart = list(email.Iterators.typed_subpart_iterator(
                            context, 'text', 'plain'))[0]
                    except IndexError:
                        subpart = None
                    if subpart:
                        s = StringIO(subpart.get_payload())
                        while True:
                            line = s.readline()
                            if not line:
                                break
                            if not line.strip():
                                continue
                            i = line.find(':')
                            if i > 0:
                                if (line[:i].lower() == 'approve' or
                                    line[:i].lower() == 'approved'):
                                    # then
                                    approved = line[i+1:].strip()
                            break
            # Is there an approved header?
            if approved is not None:
                # Does it match the list password?  Note that we purposefully
                # do not allow the site password here.
                if self.Authenticate([config.AuthListAdmin,
                                      config.AuthListModerator],
                                     approved) <> config.UnAuthorized:
                    action = config.APPROVE
                else:
                    # The password didn't match.  Re-pend the message and
                    # inform the list moderators about the problem.
                    self.pend_repend(cookie, rec)
                    raise Errors.MMBadPasswordError
            else:
                action = config.DISCARD
            try:
                self.HandleRequest(id, action)
            except KeyError:
                # Most likely because the message has already been disposed of
                # via the admindb page.
                elog.error('Could not process HELD_MESSAGE: %s', id)
            return (op,)
        elif op == Pending.RE_ENABLE:
            member = data[1]
            self.setDeliveryStatus(member, MemberAdaptor.ENABLED)
            return op, member
        else:
            assert 0, 'Bad op: %s' % op

    def ConfirmUnsubscription(self, addr, lang=None, remote=None):
        if lang is None:
            lang = self.getMemberLanguage(addr)
        cookie = self.pend_new(Pending.UNSUBSCRIPTION, addr)
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
             'requestaddr' : self.getListAddress('request'),
             'remote'      : remote,
             'listadmin'   : self.GetOwnerEmail(),
             'confirmurl'  : confirmurl,
             }, lang=lang, mlist=self)
        msg = Message.UserNotification(
            addr, self.GetRequestEmail(cookie),
            text=text, lang=lang)
            # BAW: See ChangeMemberAddress() for why we do it this way...
        del msg['subject']
        msg['Subject'] = self.GetConfirmLeaveSubject(realname, cookie)
        msg['Reply-To'] = self.GetRequestEmail(cookie)
        msg.send(self)


    #
    # Miscellaneous stuff
    #
    def HasExplicitDest(self, msg):
        """True if list name or any acceptable_alias is included among the
        addresses in the recipient headers.
        """
        # This is the list's full address.
        recips = []
        # Check all recipient addresses against the list's explicit addresses,
        # specifically To: Cc: and Resent-to:
        to = []
        for header in ('to', 'cc', 'resent-to', 'resent-cc'):
            to.extend(getaddresses(msg.get_all(header, [])))
        for fullname, addr in to:
            # It's possible that if the header doesn't have a valid RFC 2822
            # value, we'll get None for the address.  So skip it.
            if addr is None:
                continue
            addr = addr.lower()
            localpart = addr.split('@')[0]
            if (# TBD: backwards compatibility: deprecated
                    localpart == self.list_name or
                    # exact match against the complete list address
                    addr == self.fqdn_listname):
                return True
            recips.append((addr, localpart))
        # Helper function used to match a pattern against an address.
        def domatch(pattern, addr):
            try:
                if re.match(pattern, addr, re.IGNORECASE):
                    return True
            except re.error:
                # The pattern is a malformed regexp -- try matching safely,
                # with all non-alphanumerics backslashed:
                if re.match(re.escape(pattern), addr, re.IGNORECASE):
                    return True
            return False
        # Here's the current algorithm for matching acceptable_aliases:
        #
        # 1. If the pattern does not have an `@' in it, we first try matching
        #    it against just the localpart.  This was the behavior prior to
        #    2.0beta3, and is kept for backwards compatibility.  (deprecated).
        #
        # 2. If that match fails, or the pattern does have an `@' in it, we
        #    try matching against the entire recip address.
        aliases = self.acceptable_aliases.splitlines()
        for addr, localpart in recips:
            for alias in aliases:
                stripped = alias.strip()
                if not stripped:
                    # Ignore blank or empty lines
                    continue
                if '@' not in stripped and domatch(stripped, localpart):
                    return True
                if domatch(stripped, addr):
                    return True
        return False

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
                clog.error('bad bounce_matching_header line: %s\n%s',
                           self.real_name, line)
            else:
                header = line[:i]
                value = line[i+1:].lstrip()
                try:
                    cre = re.compile(value, re.IGNORECASE)
                except re.error, e:
                    # The regexp was malformed.  BAW: should do a better
                    # job of informing the list admin.
                    clog.error("""\
bad regexp in bounce_matching_header line: %s
\n%s (cause: %s)""", self.real_name, value, e)
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
            for value in msg.get_all(header, []):
                if cre.search(value):
                    return line
        return 0

    def autorespondToSender(self, sender, lang=None):
        """Return true if Mailman should auto-respond to this sender.

        This is only consulted for messages sent to the -request address, or
        for posting hold notifications, and serves only as a safety value for
        mail loops with email 'bots.
        """
        # language setting
        if lang == None:
            lang = self.preferred_language
        i18n.set_language(lang)
        # No limit
        if config.MAX_AUTORESPONSES_PER_DAY == 0:
            return 1
        today = time.localtime()[:3]
        info = self.hold_and_cmd_autoresponses.get(sender)
        if info is None or info[0] <> today:
            # First time we've seen a -request/post-hold for this sender
            self.hold_and_cmd_autoresponses[sender] = (today, 1)
            # BAW: no check for MAX_AUTORESPONSES_PER_DAY <= 1
            return 1
        date, count = info
        if count < 0:
            # They've already hit the limit for today.
            vlog.info('-request/hold autoresponse discarded for: %s', sender)
            return 0
        if count >= config.MAX_AUTORESPONSES_PER_DAY:
            vlog.info('-request/hold autoresponse limit hit for: %s', sender)
            self.hold_and_cmd_autoresponses[sender] = (today, -1)
            # Send this notification message instead
            text = Utils.maketext(
                'nomoretoday.txt',
                {'sender' : sender,
                 'listname': self.fqdn_listname,
                 'num' : count,
                 'owneremail': self.GetOwnerEmail(),
                 },
                lang=lang)
            msg = Message.UserNotification(
                sender, self.GetOwnerEmail(),
                _('Last autoresponse notification for today'),
                text, lang=lang)
            msg.send(self)
            return 0
        self.hold_and_cmd_autoresponses[sender] = (today, count+1)
        return 1

    def GetBannedPattern(self, email):
        """Returns matched entry in ban_list if email matches.
        Otherwise returns None.
        """
        return self.ban_list and self.GetPattern(email, self.ban_list)

    def HasAutoApprovedSender(self, sender):
        """Returns True and logs if sender matches address or pattern
        in subscribe_auto_approval.  Otherwise returns False.
        """
        auto_approve = False
        if self.GetPattern(sender, self.subscribe_auto_approval):
            auto_approve = True
            vlog.info('%s: auto approved subscribe from %s',
                      self.internal_name(), sender)
        return auto_approve

    def GetPattern(self, email, pattern_list):
        """Returns matched entry in pattern_list if email matches.
        Otherwise returns None.
        """
        matched = None
        for pattern in pattern_list:
            if pattern.startswith('^'):
                # This is a regular expression match
                try:
                    if re.search(pattern, email, re.IGNORECASE):
                        matched = pattern
                        break
                except re.error:
                    # BAW: we should probably remove this pattern
                    pass
            else:
                # Do the comparison case insensitively
                if pattern.lower() == email.lower():
                    matched = pattern
                    break
        return matched



    #
    # Multilingual (i18n) support
    #
    def set_languages(self, *language_codes):
        # XXX FIXME not to use a database entity directly.
        from Mailman.database.model import Language
        # Don't use the language_codes property because that will add the
        # default server language.  The effect would be that the default
        # server language would never get added to the list's list of
        # languages.
        requested_codes = set(language_codes)
        enabled_codes = set(config.languages.enabled_codes)
        self.available_languages = [
            Language(code) for code in requested_codes & enabled_codes]

    def add_language(self, language_code):
        self.available_languages.append(Language(language_code))

    @property
    def language_codes(self):
        # Callers of this method expect a list of language codes
        available_codes = set(self.available_languages)
        enabled_codes = set(config.languages.enabled_codes)
        codes = available_codes & enabled_codes
        # If we don't add this, and the site admin has never added any
        # language support to the list, then the general admin page may have a
        # blank field where the list owner is supposed to chose the list's
        # preferred language.
        if config.DEFAULT_SERVER_LANGUAGE not in codes:
            codes.add(config.DEFAULT_SERVER_LANGUAGE)
        return list(codes)
