# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

"""Built-in pipelines."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BasePipeline',
    'OwnerPipeline',
    'PostingPipeline',
    'VirginPipeline',
    'initialize',
    'process',
    ]


import logging

from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.app.bounces import bounce_message
from mailman.app.finder import find_components
from mailman.config import config
from mailman.core import errors
from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler
from mailman.interfaces.pipeline import IPipeline

dlog = logging.getLogger('mailman.debug')
vlog = logging.getLogger('mailman.vette')



def process(mlist, msg, msgdata, pipeline_name='built-in'):
    """Process the message through the given pipeline.

    :param mlist: the IMailingList for this message.
    :param msg: The Message object.
    :param msgdata: The message metadata dictionary.
    :param pipeline_name: The name of the pipeline to process through.
    """
    message_id = msg.get('message-id', 'n/a')
    pipeline = config.pipelines[pipeline_name]
    for handler in pipeline:
        dlog.debug('{0} pipeline {1} processing: {2}'.format(
            message_id, pipeline_name, handler.name))
        try:
            handler.process(mlist, msg, msgdata)
        except errors.DiscardMessage as error:
            vlog.info(
                '{0} discarded by "{1}" pipeline handler "{2}": {3}'.format(
                    message_id, pipeline_name, handler.name, error.message))
        except errors.RejectMessage as error:
            vlog.info(
                '{0} rejected by "{1}" pipeline handler "{2}": {3}'.format(
                    message_id, pipeline_name, handler.name, error.message))
            bounce_message(mlist, msg, error)



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



class OwnerPipeline(BasePipeline):
    """The built-in owner pipeline."""

    name = 'default-owner-pipeline'
    description = _('The built-in owner pipeline.')

    _default_handlers = (
        'owner-recipients',
        'to-outgoing',
        )


class PostingPipeline(BasePipeline):
    """The built-in posting pipeline."""

    name = 'default-posting-pipeline'
    description = _('The built-in posting pipeline.')

    _default_handlers = (
        'mime-delete',
        'tagger',
        'member-recipients',
        'avoid-duplicates',
        'cleanse',
        'cleanse-dkim',
        'cook-headers',
        'rfc-2369',
        'to-archive',
        'to-digest',
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
    for handler_class in find_components('mailman.handlers', IHandler):
        handler = handler_class()
        verifyObject(IHandler, handler)
        assert handler.name not in config.handlers, (
            'Duplicate handler "{0}" found in {1}'.format(
                handler.name, handler_class))
        config.handlers[handler.name] = handler
    # Set up some pipelines.
    for pipeline_class in (OwnerPipeline, PostingPipeline, VirginPipeline):
        pipeline = pipeline_class()
        config.pipelines[pipeline.name] = pipeline
