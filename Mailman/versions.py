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

def UpdateOldVars(l, stored_state):
    """Transform old variable values into new ones, deleting old ones.
    stored_state is last snapshot from file, as opposed to from InitVars()."""

    def PreferStored(oldname, newname, l=l, state=stored_state):
        "Use specified value if new value does not come from stored state."
        if hasattr(l, oldname):
            if not state.has_key(newname):
                setattr(l, newname, getattr(l, oldname))
            delattr(l, oldname)

    #                  Pre 1.0b1.2, klm 04/11/1998.
    #  - migrated vars:
    PreferStored('auto_subscribe', 'open_subscribe')
    PreferStored('closed', 'private_roster')
    PreferStored('mimimum_post_count_before_removal',
                 'mimimum_post_count_before_bounce_action')
    PreferStored('bad_posters', 'forbidden_posters')
    PreferStored('automatically_remove', 'automatic_bounce_action')
    #  - dropped vars:
    for a in ['archive_retain_text_copy',
              'archive_update_frequency',
              'archive_volume_frequency']:
        if hasattr(l, a): delattr(l, a)

def UpdateOldUsers(l):
    """Transform sense of changed user options."""
    if older(l.data_version, "1.0b1.2"):
        # Mime-digest bitfield changed from Enable to Disable after 1.0b1.1.
        for m in l.members + l.digest_members:
            was = l.GetUserOption(m, mm_cfg.DisableMime)
            l.SetUserOption(m, mm_cfg.DisableMime, not was)

def older(version, reference):
    """True if version is older than current.

    Different numbering systems imply version is older."""
    if type(version) != type(reference):
      return 1
    if version >= reference:
      return 0  
    else:
      return 1
    # Iterate over the repective contiguous sections of letters and digits
    # until a section from the reference is found to be different than the
    # corresponding version section, and return the sense of the
    # difference.  If no differences are found, then 0 is returned.
    #for v, r in map(None, section(version), section(reference)):
     #   if r == None:
            # Reference is a full release and version is an interim - eg,
            # alpha or beta - which precede full, are older:
      #      return 1
       # if type(v) != type(r):
        #    # Numbering system changed.
         #   return 1
       # if v < r:
        #    return 1
       # if v > r:
        #    return 0
    # return 0
    
#def section(s):
#    """Split string into contiguous sequences of letters and digits."""
#    section = ""
#    got = []
#    wasat = ""
#    for c in s:
#        if c in string.letters:
#            at = string.letters; add = c
#        elif c in string.digits:
#            at = string.digits; add = c
#        else:
#            at = ""; add = ""
#
#        if at == wasat:                 # In continuous sequence.
#            section = section + add
#        else:                           # Switching.
#            if section:
#                if wasat == string.digits:
#                    section = int(section)
#                got.append(section)
#            section = add
#            wasat = at
#    if section:                         # Get trailing stuff.
#        if wasat == string.digits:
#            section = int(section)
#        got.append(section)
#    return got
