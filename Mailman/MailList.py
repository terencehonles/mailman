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

from __future__ import with_statement

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
from Mailman.Digester import Digester
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
class MailList(object, Archiver, Digester, SecurityManager, Bouncer):

    implements(
        IMailingList,
        IMailingListAddresses,
        IMailingListIdentity,
        IMailingListRosters,
        )

    def __init__(self, data):
        self._data = data
        # Only one level of mixin inheritance allowed.
        for baseclass in self.__class__.__bases__:
            if hasattr(baseclass, '__init__'):
                baseclass.__init__(self)
        # Initialize the web u/i components.
        self._gui = []
        for component in dir(Gui):
            if component.startswith('_'):
                continue
            self._gui.append(getattr(Gui, component)())
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
            return getattr(super(MailList, self), name)
        # Delegate to the database model object if it has the attribute.
        obj = getattr(self._data, name, missing)
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
        return '<mailing list "%s" at %x>' % (self.fqdn_listname, id(self))


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
        pattern = Utils.get_pattern(invitee, self.ban_list)
        if pattern:
            raise Errors.MembershipIsBanned(pattern)
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
        pattern = Utils.get_pattern(email, self.ban_list)
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
        pattern = Utils.get_pattern(newaddr, self.ban_list)
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
        pattern = Utils.get_pattern(newaddr, self.ban_list)
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
            if Utils.get_pattern(newaddr, mlist.ban_list):
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
            with i18n.using_language(self.preferred_language):
                realname = self.real_name
                subject = _('%(realname)s address change notification')
            name = self.getMemberName(newaddr)
            if name is None:
                name = ''
            if isinstance(name, unicode):
                name = name.encode(Utils.GetCharSet(self.preferred_language),
                                   'replace')
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

    def HasAutoApprovedSender(self, sender):
        """Returns True and logs if sender matches address or pattern
        in subscribe_auto_approval.  Otherwise returns False.
        """
        auto_approve = False
        if Utils.get_pattern(sender, self.subscribe_auto_approval):
            auto_approve = True
            vlog.info('%s: auto approved subscribe from %s',
                      self.internal_name(), sender)
        return auto_approve


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
