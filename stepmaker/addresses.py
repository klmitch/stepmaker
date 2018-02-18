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

import six


@six.python_2_unicode_compatible
class StepAddress(object):
    """
    Represent an "address".  An address is a filename and a path
    through that file to a particular item, usually of configuration.
    The path consists of "/"-separated dictionary keys and
    bracket-enclosed list indices; for example, the 5th element of the
    "bar" key of the 3rd element of the "foo" key in the file
    "spam.yaml" would be rendered as "spam.yaml:/foo[3]/bar[5]".

    Note that a ``StepAddress`` instance is immutable; to obtain
    addresses that contain additional keys or list indices, use the
    ``key()`` and ``idx()`` methods to return new ``StepAddress``
    instances with the additional paths.
    """

    def __init__(self, filename, path=''):
        """
        Initialize a ``StepAddress`` instance.

        :param str filename: The name of the file.
        :param str path: An optional initial path.
        """

        self.filename = filename
        self.path = path

    def __str__(self):
        """
        Return a string representation of the address.

        :returns: The filename and path, separated by a ":".
        :rtype: ``str``
        """

        return '%s:%s' % (self.filename, self.path)

    def key(self, key):
        """
        Construct a new address with an additional dictionary key.

        :param str key: The key to add to the path.

        :returns: The new address.
        :rtype: ``StepAddress``
        """

        return self.__class__(self.filename, self.path + '/%s' % key)

    def idx(self, idx):
        """
        Construct a new address with an additional list index.

        :param int idx: The index to add to the path.

        :returns: The new address.
        :rtype: ``StepAddress``
        """

        return self.__class__(self.filename, self.path + '[%d]' % idx)
