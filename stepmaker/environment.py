# Copyright (C) 2018 by Kevin L. Mitchell <klmitch@mit.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

import collections
import os
import shlex
import subprocess
import sys

import six

from stepmaker import exceptions
from stepmaker import utils


# Sentinel to indicate no default passed to get_raw()
_unset = object()

# For convenience
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT


class CompletedProcess(object):
    """
    Represent a completed process.  All available information from the
    process execution is available under the ``args``, ``returncode``,
    ``stdout``, and ``stderr`` attributes.
    """

    def __init__(self, args, returncode, stdout=None, stderr=None):
        """
        Initialize a ``CompletedProcess`` instance.

        :param args: A list of arguments, including the executable.
        :type args: ``list`` of ``str``
        :param int returncode: The return code of the process.
        :param str stdout: The output to standard output.
        :param str stderr: The output to standard error.
        """

        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Environment(collections.MutableMapping):
    """
    Represent an execution environment.  This is a dictionary-like
    class containing environment variables, but a current working
    directory (divorced from the process's current working directory)
    is also maintained.  Files can be opened relative to the
    environment's working directory, and shell commands can be invoked
    by either calling the environment with the appropriate arguments
    (see the ``__call__()`` method documentation) or by calling the
    ``popen()`` method (which returns a ``subprocess.Popen`` object).
    """

    def __init__(self, environ=None, cwd=None, **specials):
        """
        Initialize an ``Environment`` instance.

        :param environ: A dictionary of environment variables.
                        Defaults to the process's current environment.
                        Note that changes to ``os.environ`` will not
                        be reflected after the ``Environment`` class
                        is instantiated.
        :type environ: ``dict`` mapping ``str`` to ``str``
        :param str cwd: The current working directory.  Defaults to
                        the process's current working directory.
        :param specials: Extra keyword arguments are interpreted as
                         factory functions for special interpreters of
                         specific environment variables.  The factory
                         functions registered this way will be called
                         with this ``Environment`` instance and the
                         variable name, and must return an object
                         responding to the ``set()`` and ``delete()``
                         methods, as well as the ``raw`` property.
                         These specials may also be registered (or
                         unregistered) after instantiation using the
                         ``register()`` method.
        """

        # Set up the base values
        self._environ = environ or os.environ.copy()
        self._cwd = utils._canonicalize_path(os.getcwd(), cwd or os.curdir)
        self._specials = specials

        # Cache of bound specials
        self._special_cache = {}

    def __len__(self):
        """
iter(        Return the number of environment variables.

        :returns: The number of environment variables present.
        :rtype: ``int``
        """

        return len(self._environ)

    def __iter__(self):
        """
        Obtain an iterator over the environment variable names.

        :returns: An iterator producing environment variable names.
        """

        return iter(self._environ)

    def __getitem__(self, name):
        """
        Retrieve the value of an environment variable.

        :param str name: The name of the environment variable.

        :returns: The value of the environment variable.  Note that
                  this may not be a string if a special has been
                  registered for this variable.

        :raises KeyError:
            The environment variable is not set.
        """

        # Is the variable even set?
        if name not in self._environ:
            raise KeyError(name)

        # Retrieve the special object
        if name in self._specials:
            return self._get_special(name)

        # OK, return the raw value
        return self._environ[name]

    def __setitem__(self, name, value):
        """
        Set the value of an environment variable.

        :param str name: The name of the environment variable.
        :param value: The new value of the environment variable.  For
                      most environment variables, this must be a
                      string; however, environment variables with a
                      registered special may accept other, compatible
                      values.
        """

        if name in self._specials:
            # If it's a special, defer to its set() method
            self._get_special(name).set(value)
        else:
            self._environ[name] = value

    def __delitem__(self, name):
        """
        Delete an environment variable.

        :param str name: The name of the environment variable.

        :raises KeyError:
            The environment variable is not set.
        """

        # Is the variable even set?
        if name not in self._environ:
            raise KeyError(name)

        # If there's a special, defer to its delete() method
        if name in self._specials:
            self._get_special(name).delete()
        else:
            del self._environ[name]

    def __call__(self, args, **kwargs):
        """
        Invoke and then wait for a shell command.  Accepts the same
        keyword arguments as ``subprocess.Popen``, with the additions
        documented below.  Note that, for convenience, the
        ``subprocess.PIPE`` and ``subprocess.STDOUT`` values are
        copied into this package.

        :param args: The shell command.  May be either a list of
                     strings, or a string that will be split using
                     ``shlex.split()``.
        :param str input: A keyword-only argument.  Provides input to
                          send to the standard input of the process.
                          Note that this is incompatible with the
                          ``subprocess.Popen`` ``stdin`` argument.
        :param bool check: A keyword-only argument.  If ``True``, the
                           return code of the command will be checked,
                           and, if non-zero, a
                           ``stepmaker.ProcessError`` exception will
                           be raised.

        :returns: The result of calling the shell command.
        :rtype: ``stepmaker.CompletedProcess``
        """

        # Check for input argument conflict
        if 'input' in kwargs and 'stdin' in kwargs:
            raise ValueError('Cannot use both "input" and "stdin" arguments')
        input_ = kwargs.pop('input', None)
        if input_:
            kwargs['stdin'] = PIPE

        # Figure out if we're to check the result
        check = kwargs.pop('check', False)

        # Convert string args into a sequence
        if isinstance(args, six.string_types):
            args = shlex.split(args)

        # Initiate the process
        process = self._system(args, kwargs)

        # Send it input and wait for it to complete
        try:
            stdout, stderr = process.communicate(input_)
        except Exception:
            exc_data = sys.exc_info()
            process.kill()
            process.wait()
            six.reraise(*exc_data)

        # Grab the return code and construct a CompletedProcess
        result = CompletedProcess(args, process.poll(), stdout, stderr)
        if check and result.returncode != 0:
            # Check if we need to raise an error
            raise exceptions.ProcessError(result)

        return result

    def _get_special(self, name):
        """
        Retrieve the special bound to a particular environment variable.
        It is assumed a special is registered; it will be called with
        this ``Environment`` instance and the environment variable
        name.

        :param str name: The name of the environment variable.

        :returns: The instance of the special.
        """

        # Create and cache the special, if necessary
        if name not in self._special_cache:
            self._special_cache[name] = self._specials[name](self, name)

        return self._special_cache[name]

    def _set(self, name, value):
        """
        Sets the value of an environment variable directly, without
        deferring to any specials set on that environment variable.
        This method is provided for the use of the specials
        themselves, and is not intended for use by ``Environment``
        consumers.

        :param str name: The name of the environment variable to set.
        :param str value: The value to set the environment variable
                          to.
        """

        self._environ[name] = value

    def _delete(self, name):
        """
        Deletes an environment variable directly, without deferring to any
        specials set on that environment variable.  This method is
        provided for the use of the specials themselves, and is not
        intended for use by ``Environment`` consumers.

        :param str name: The name of the environment variable to delete.
        """

        self._environ.pop(name, None)

    def _system(self, args, kwargs):
        """
        Invoke a shell command.  This is the common part of the
        ``__call__()`` and ``popen()`` methods.

        :param args: The list of arguments.
        :type args: ``list`` of ``str``
        :param kwargs: The keyword arguments to pass to
                       ``subprocess.Popen``.
        :type kwargs: ``dict``

        :returns: The process object.
        :rtype: ``subprocess.Popen``
        """

        # Interpret cwd relative to ours
        kwargs['cwd'] = (
            self.filename(kwargs['cwd']) if 'cwd' in kwargs else self._cwd
        )

        # Use us as the environment
        kwargs.setdefault('env', self._environ)

        # Set a default for close_fds
        kwargs.setdefault('close_fds', True)

        return subprocess.Popen(args, **kwargs)

    def setdefault(self, key, default=None):
        """
        Set the default value for an environment variable.

        :param str key: The name of the environment variable.
        :param default: The default value of the environment variable.

        :returns: The value of the environment variable.
        """

        # Note: Need this override because the default implementation
        # returns default unchanged if it sets it, but we need to
        # engage our specials behavior

        # Set the key if it's not already set
        if key not in self._environ:
            self[key] = default

        # This will capture any transformations
        return self[key]

    def copy(self):
        """
        Create a shallow copy of this ``Environment`` instance.

        :returns: A shallow, decoupled copy of this ``Environment``
                  instance.
        :rtype: ``Environment``
        """

        return self.__class__(
            self._environ.copy(), self._cwd, **self._specials
        )

    def register(self, name, special=None):
        """
        Register (or deregister) a factory function for special
        environment variables.  This allows additional specials not
        passed to the constructor to be registered, or, if the
        ``special`` parameter is specified as ``None`` or not
        provided, allows existing specials to be "deregistered".

        :param str name: The name of the environment variable.
        :param special: A factory function for a special interpreter
                        of the environment variable.  The factory
                        function will be called with this
                        ``Environment`` instance and the variable
                        name, and must return an object responding to
                        the ``set()`` and ``delete()`` methods, as
                        well as the ``raw`` property.  If this
                        parameter is not provided, or is set to
                        ``None``, any existing special will be
                        deregistered.

        :returns: The previously registered special factory, or
                  ``None`` if none was registered.
        """

        # Do nothing if the special factory is the same
        if self._specials.get(name) == special:
            return self._specials.get(name)

        # Invalidate the special cache
        self._special_cache.pop(name, None)

        # Unregister the current special factory
        old = self._specials.pop(name, None)
        if special is not None:
            # Register the new special factory
            self._specials[name] = special

        return old

    def get_raw(self, name, default=_unset):
        """
        Get the raw value of an environment variable, regardless of any
        specials that may be set for that variable.

        :param str name: The name of the environment variable.
        :param default: A default to return, if the environment
                        variable is not set.  If not provided, a
                        ``KeyError`` will be raised in that case.

        :returns: The value of the environment variable.
        :rtype: ``str``

        :raises KeyError:
            The named environment variable does not exist, and
            ``default`` was not provided.
        """

        # Handle the case of a missing variable and no default
        if default is _unset and name not in self._environ:
            raise KeyError(name)

        return self._environ.get(name, default)

    def filename(self, filename):
        """
        Resolve the full path to a given file relative to the current
        working directory of this environment.

        :param str filename: The filename to resolve.

        :returns: The absolute path to the file.
        :rtype: ``str``
        """

        return utils._canonicalize_path(self._cwd, filename)

    def open(self, filename, mode='r', buffering=-1):
        """
        Open a file relative to the current working directory of this
        environment.

        :param str filename: The filename to open.
        :param str mode: The mode with which to open the file.
                         Defaults to 'r'.
        :param int buffering: The buffering mode.  Has the same
                              meaning as the ``open()`` built-in.

        :returns: The open file.
        :rtype: ``file``

        :raises IOError:
            Failed to open the file.
        """

        return open(self.filename(filename), mode, buffering)

    def popen(self, args, **kwargs):
        """
        Invoke a shell command.  Accepts the same keyword arguments as
        ``subprocess.Popen``.  Unlike the ``__call__()`` method, this
        method does not wait for the command to complete execution;
        instead, the ``subprocess.Popen`` object is returned to the
        caller.  Also note that, for convenience, the
        ``subprocess.PIPE`` and ``subprocess.STDOUT`` values are
        copied into this package.

        :param args: The shell command.  May be either a list of
                     strings, or a string that will be split using
                     ``shlex.split()``.

        :returns: The process object.
        :rtype: ``subprocess.Popen``
        """

        # Convert string args into a sequence
        if isinstance(args, six.string_types):
            args = shlex.split(args)

        return self._system(args, kwargs)

    @property
    def cwd(self):
        """
        The current working directory of this environment.  When set,
        relative paths will be interpreted relative to the
        environment's working directory.
        """

        return self._cwd

    @cwd.setter
    def cwd(self, value):
        """
        Set the current working directory of this environment.

        :param str value: The path to the new working directory for
                          the environment.  Will be interpreted
                          relative to the current working directory.
        """

        self._cwd = self.filename(value)
