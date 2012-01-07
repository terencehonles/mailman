# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Individualized delivery with header/footer decorations."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DecoratingDelivery',
    'DecoratingMixin',
    ]


from mailman.config import config
from mailman.mta.verp import VERPDelivery



class DecoratingMixin:
    """Decorate a message with recipient-specific headers and footers."""

    def decorate(self, mlist, msg, msgdata):
        """Add recipient-specific headers and footers."""
        decorator = config.handlers['decorate']
        decorator.process(mlist, msg, msgdata)
        # Do not decorate a message more than once.
        msgdata['nodecorate'] = True



class DecoratingDelivery(DecoratingMixin, VERPDelivery):
    """Add recipient-specific headers and footers."""

    def __init__(self):
        """See `IndividualDelivery`."""
        super(DecoratingDelivery, self).__init__()
        self.callbacks.append(self.decorate)
