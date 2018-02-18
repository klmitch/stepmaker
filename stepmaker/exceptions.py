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

import signal

import six


class StepError(Exception):
    """
    Report a step configuration error.  The address, if provided, will
    be stored in the ``addr`` attribute.
    """

    def __init__(self, msg, addr=None):
        """
        Initialize a ``StepError`` instance.

        :param str msg: A message describing the error.
        :param addr: The address at which the error occurred.
        :type addr: ``StepAddress``
        """

        # Add the address to the message
        if addr is not None:
            msg += ' (%s)' % addr

        # Initialize the exception
        super(StepError, self).__init__(msg)

        # Save the address
        self.addr = addr


# Sentinel that an action was skipped
skipped = object()


class AbortStep(Exception):
    """
    An exception that can be raised by ``Modifier.pre_call()`` to
    abort a step.  This is treated as non-fatal by the step processing
    logic, and will abort further ``Modifier`` and ``Action``
    processing in the step.
    """

    def __init__(self, result=skipped):
        """
        Initialize an ``AbortStep`` instance.

        :param result: The result to return from the step.  If not
                       provided, the step processing logic will
                       continue as if the step was completely skipped.
        """

        super(AbortStep, self).__init__()
        self.result = result


class ProcessError(Exception):
    """
    An exception raised when a process executed through the facilities
    provided by the ``stepmaker.Environment`` class exits with a
    non-zero return code.
    """

    def __init__(self, result):
        """
        Initialize a ``ProcessError`` exception.

        :param result: The result of the process execution.
        :type result: ``stepmaker.CompletedProcess``
        """

        # Construct a message
        if result.returncode and result.returncode < 0:
            # Died due to a signal; figure out the signal name
            signame = None

            # Try the Python 3 method of resolving the signal name
            if six.PY3:  # pragma: no cover
                try:
                    signame = signal.Signals(-result.returncode).name
                except AttributeError:
                    # Doesn't have Signals, we'll fall back to the
                    # Python 2 method
                    pass
                except ValueError:
                    signame = 'unknown signal %d' % -result.returncode

            if signame is None:  # pragma: no cover
                # Python 2 version of signal name lookup
                for name, value in signal.__dict__.items():
                    if (name.startswith('SIG') and
                            not name.startswith('SIG_') and
                            value == -result.returncode):
                        signame = name
                        break

            if signame is None:
                # Guess we don't know the signal name
                signame = 'unknown signal %d' % -result.returncode

            super(ProcessError, self).__init__(
                'Command "%s" died with %s' % (result.args[0], signame)
            )
        elif result.returncode:
            # Non-zero error code
            super(ProcessError, self).__init__(
                'Command "%s" returned non-zero exit status %d' %
                (result.args[0], result.returncode)
            )
        else:
            # Did it really fail?
            super(ProcessError, self).__init__(
                'Command "%s" successful' % result.args[0]
            )

        self.result = result
