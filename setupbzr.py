# setuptools plugin for bzr
# Barry Warsaw <barry@python.org>

# Use by adding this to your setuptools.file_finders entry point:
# 'bzr = bzrplug:find_files_for_bzr'

# http://peak.telecommunity.com/DevCenter/setuptools#adding-support-for-other-revision-control-systems

import os
import bzrlib.branch


def get_children(path):
    # Open an existing branch which contains the url.
    branch, inpath = bzrlib.branch.Branch.open_containing(path)
    # Get the inventory of the branch's last revision.
    inv = branch.repository.get_revision_inventory(branch.last_revision())
    # Get the inventory entry for the path.
    entry = inv[inv.path2id(path)]
    # Return the names of the children.
    return [os.path.join(path, child) for child in entry.children.keys()]


def find_files_for_bzr(dirname):
    bzrfiles = []
    search = [dirname]
    while search:
        current = search.pop(0)
        children = get_children(current)
        bzrfiles.extend(children)
        search.extend([child for child in children if os.path.isdir(child)])
    return bzrfiles
