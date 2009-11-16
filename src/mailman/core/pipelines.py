# Copyright (C) 2008-2009 by the Free Software Foundation, Inc.
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

"""Pipeline processor."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'initialize',
    'process',
    ]


from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.app.finder import find_components
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler
from mailman.interfaces.pipeline import IPipeline



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



class BasePipeline:
    """Base pipeline implementation."""

    implements(IPipeline)

    _default_handlers = ()

    def __init__(self):
        self._handlers = []
        for handler_name in self._default_handlers:
            self._handlers.append(config.handlers[handler_name])

    def __iter__(self):
        """See `IPipeline`."""
        for handler in self._handlers:
            yield handler


class BuiltInPipeline(BasePipeline):
    """The built-in pipeline."""

    name = 'built-in'
    description = _('The built-in pipeline.')

    _default_handlers = (
        'mime-delete',
        'scrubber',
        'tagger',
        'calculate-recipients',
        'avoid-duplicates',
        'cleanse',
        'cleanse-dkim',
        'cook-headers',
        'to-digest',
        'to-archive',
        'to-usenet',
        'after-delivery',
        'acknowledge',
        'to-outgoing',
        )


class VirginPipeline(BasePipeline):
    """The processing pipeline for virgin messages.

    Virgin messages are those that are crafted internally by Mailman.
    """
    name = 'virgin'
    description = _('The virgin queue pipeline.')

    _default_handlers = (
        'cook-headers',
        'to-outgoing',
        )



def initialize():
    """Initialize the pipelines."""
    # Find all handlers in the registered plugins.
    for handler_class in find_components('mailman.pipeline', IHandler):
        handler = handler_class()
        verifyObject(IHandler, handler)
        assert handler.name not in config.handlers, (
            'Duplicate handler "{0}" found in {1}'.format(
                handler.name, handler_finder))
        config.handlers[handler.name] = handler
    # Set up some pipelines.
    for pipeline_class in (BuiltInPipeline, VirginPipeline):
        pipeline = pipeline_class()
        config.pipelines[pipeline.name] = pipeline
