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


"""Routines which rectify an old maillist with current maillist structure.

The maillist .CheckVersion() method looks for an old .data_version
setting in the loaded maillist structure, and if found calls the
Update() routine from this module, supplying the list and the state
last loaded from storage.  (Th state is necessary to distinguish from
default assignments done in the .InitVars() methods, before
.CheckVersion() is called.)

For new versions you should add sections to the UpdateOldVars() and the
UpdateOldUsers() sections, to preserve the sense of settings across
structural changes.  Note that the routines have only one pass - when
.CheckVersions() finds a version change it runs this routine and then
updates the data_version number of the list, and then does a .Save(), so
the transformations won't be run again until another version change is
detected."""


import re, string, types
import mm_cfg

def Update(l, stored_state):
    "Dispose of old vars and user options, mapping to new ones when suitable."
    # No worry about entirely new vars because InitVars() takes care of them.
    UpdateOldVars(l, stored_state)
    UpdateOldUsers(l)

uniqueval = []
def UpdateOldVars(l, stored_state):
    """Transform old variable values into new ones, deleting old ones.
    stored_state is last snapshot from file, as opposed to from InitVars()."""

    def PreferStored(oldname, newname, newdefault=uniqueval,
                     l=l, state=stored_state):
        """Use specified old value if new value does is not in stored state.

        If the old attr does not exist, and no newdefault is specified, the 
        new attr is *not* created - so either specify a default or be
        positive that the old attr exists - or don't depend on the new attr."""
        if hasattr(l, oldname):
            if not state.has_key(newname):
                setattr(l, newname, getattr(l, oldname))
            delattr(l, oldname)
        if not hasattr(l, newname) and newdefault is not uniqueval:
                setattr(l, newname, newdefault)

    # Migrate to 1.0b6, klm 10/22/1998:
    PreferStored('reminders_to_admins', 'umbrella_list',
                 mm_cfg.DEFAULT_UMBRELLA_LIST)

    # Migrate up to 1.0b5:
    PreferStored('auto_subscribe', 'open_subscribe')
    PreferStored('closed', 'private_roster')
    PreferStored('mimimum_post_count_before_removal',
                 'mimimum_post_count_before_bounce_action')
    PreferStored('bad_posters', 'forbidden_posters')
    PreferStored('automatically_remove', 'automatic_bounce_action')
    if hasattr(l, "open_subscribe"):
        if l.open_subscribe:
            if mm_cfg.ALLOW_OPEN_SUBSCRIBE:
                l.subscribe_policy = 0 
            else:
                l.subscribe_policy = 1
        else:
            l.subscribe_policy = 2      # admin approval
        delattr(l, "open_subscribe")
    if not hasattr(l, "administrivia"):
        setattr(l, "administrivia", mm_cfg.DEFAULT_ADMINISTRIVIA)
    if not hasattr(l, "admin_member_chunksize"):
        setattr(l, "admin_member_chunksize",
                mm_cfg.DEFAULT_ADMIN_MEMBER_CHUNKSIZE)
    #
    # this attribute was added then deleted, so there are a number of
    # cases to take care of
    #
    if hasattr(l, "posters_includes_members"): 
        if l.posters_includes_members:
            if l.posters:
                l.member_posting_only = 1
        else:
            if l.posters:
                l.member_posting_only = 0
        delattr(l, "posters_includes_members")
    else: # make sure everyone gets the behavior the list used to have
        if l.posters:
            l.member_posting_only = 0
    #
    # transfer the list data type for holding members and digest members
    # to the dict data type starting file format version 11
    #
    if type(l.members) is type([]):
        members = {}
        for m in l.members:
            members[m] = 1
        l.members = members
    if type(l.digest_members) is type([]):
        dmembers = {}
        for dm in l.digest_members:
            dmembers[dm] = 1
        l.digest_members = dmembers
    #
    # set admin_notify_mchanges
    #
    if not hasattr(l, "admin_notify_mchanges"):
        setatrr(l, "admin_notify_mchanges",
                mm_cfg.DEFAULT_ADMIN_NOTIFY_MCHANGES)


def UpdateOldUsers(l):
    """Transform sense of changed user options."""
    # Currently nothing to do.
    pass

def older(version, reference):
    """True if version is older than current.

    Different numbering systems imply version is older."""
    if type(version) != type(reference):
      return 1
    if version >= reference:
      return 0  
    else:
      return 1
