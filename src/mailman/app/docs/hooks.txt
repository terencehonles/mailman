=====
Hooks
=====

Mailman defines two initialization hooks, one which is run early in the
initialization process and the other run late in the initialization process.
Hooks name an importable callable so it must be accessible on ``sys.path``.
::

    >>> import os, sys
    >>> from mailman.config import config
    >>> config_directory = os.path.dirname(config.filename)
    >>> sys.path.insert(0, config_directory)

    >>> hook_path = os.path.join(config_directory, 'hooks.py')
    >>> with open(hook_path, 'w') as fp:
    ...     print >> fp, """\
    ... counter = 1
    ... def pre_hook():
    ...     global counter
    ...     print 'pre-hook:', counter
    ...     counter += 1
    ...
    ... def post_hook():
    ...     global counter
    ...     print 'post-hook:', counter
    ...     counter += 1
    ... """
    >>> fp.close()


Pre-hook
========

We can set the pre-hook in the configuration file.

    >>> config_path = os.path.join(config_directory, 'hooks.cfg')
    >>> with open(config_path, 'w') as fp:
    ...     print >> fp, """\
    ... [meta]
    ... extends: test.cfg
    ...
    ... [mailman]
    ... pre_hook: hooks.pre_hook
    ... """

The hooks are run in the second and third steps of initialization.  However,
we can't run those initialization steps in process, so call a command line
script that will produce no output to force the hooks to run.
::

    >>> import subprocess
    >>> from mailman.testing.layers import ConfigLayer
    >>> def call():
    ...     proc = subprocess.Popen(
    ...         'bin/mailman lists --domain ignore -q'.split(),
    ...         cwd=ConfigLayer.root_directory,
    ...         env=dict(MAILMAN_CONFIG_FILE=config_path,
    ...                  PYTHONPATH=config_directory),
    ...         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ...     stdout, stderr = proc.communicate()
    ...     assert proc.returncode == 0, stderr
    ...     print stdout

    >>> call()
    pre-hook: 1
    <BLANKLINE>

    >>> os.remove(config_path)


Post-hook
=========

We can set the post-hook in the configuration file.
::

    >>> with open(config_path, 'w') as fp:
    ...     print >> fp, """\
    ... [meta]
    ... extends: test.cfg
    ...
    ... [mailman]
    ... post_hook: hooks.post_hook
    ... """

    >>> call()
    post-hook: 1
    <BLANKLINE>

    >>> os.remove(config_path)


Running both hooks
==================

We can set the pre- and post-hooks in the configuration file.
::

    >>> with open(config_path, 'w') as fp:
    ...     print >> fp, """\
    ... [meta]
    ... extends: test.cfg
    ...
    ... [mailman]
    ... pre_hook: hooks.pre_hook
    ... post_hook: hooks.post_hook
    ... """

    >>> call()
    pre-hook: 1
    post-hook: 2
    <BLANKLINE>
