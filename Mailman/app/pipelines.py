# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""Pipeline processor."""

__metaclass__ = type
__all__ = [
    'initialize',
    'process',
    ]


from zope.interface import implements
from zope.interface.verify import verifyObject

from Mailman.app.plugins import get_plugins
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.interfaces import IHandler, IPipeline



def process(mlist, msg, msgdata, pipeline_name='built-in'):
    """Process the message through the given pipeline.

    :param mlist: the IMailingList for this message.
    :param msg: The Message object.
    :param msgdata: The message metadata dictionary.
    :param pipeline_name: The name of the pipeline to process through.
    """
    pipeline = config.pipelines[pipeline_name]
    for handler in pipeline:
        handler.process(mlist, msg, msgdata)



class BuiltInPipeline:
    """The built-in pipeline."""

    implements(IPipeline)

    name = 'built-in'
    description = _('The built-in pipeline.')

    _default_handlers = (
        'mimedel',
        'scrubber',
        'tagger',
        'calculate-recipients',
        'avoid-duplicates',
        'cleanse',
        'cleanse_dkim',
        'cook_headers',
        'to_digest',
        'to_archive',
        'to_usenet',
        'after_delivery',
        'acknowledge',
        'to_outgoing',
        )

    def __init__(self):
        self._handlers = []
        for handler_name in self._default_handlers:
            self._handler.append(config.handlers[handler_name])

    def __iter__(self):
        """See `IPipeline`."""
        for handler in self._handlers:
            yield handler



def initialize():
    """Initialize the pipelines."""
    # Find all handlers in the registered plugins.
    for handler_finder in get_plugins('mailman.handlers'):
        for handler_class in handler_finder():
            handler = handler_class()
            verifyObject(IHandler, handler)
            assert handler.name not in config.handlers, (
                'Duplicate handler "%s" found in %s' %
                (handler.name, handler_finder))
            config.handlers[handler.name] = handler
