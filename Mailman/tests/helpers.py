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

"""Various test helpers."""

__metaclass__ = type
__all__ = [
    'get_queue_messages',
    'make_testable_runner',
    ]



def make_testable_runner(runner_class):
    """Create a queue runner that runs until its queue is empty.

    :param runner_class: An IRunner
    :return: A runner instance.
    """

    class EmptyingRunner(runner_class):
        """Stop processing when the queue is empty."""

        def _doperiodic(self):
            """Stop when the queue is empty."""
            self._stop = (len(self._switchboard.files) == 0)

    return EmptyingRunner()



class _Bag:
    def __init__(self, **kws):
        for key, value in kws.items():
            setattr(self, key, value)


def get_queue_messages(queue):
    """Return and clear all the messages in the given queue.

    :param queue: An ISwitchboard
    :return: A list of 2-tuples where each item contains the message and
        message metadata.
    """
    messages = []
    for filebase in queue.files:
        msg, msgdata = queue.dequeue(filebase)
        messages.append(_Bag(msg=msg, msgdata=msgdata))
        queue.finish(filebase)
    return messages
