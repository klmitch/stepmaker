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

import abc
import collections
import functools
import os

import six


@six.add_metaclass(abc.ABCMeta)
class Special(object):
    """
    Abstract superclass for all ``Environment`` specials.  A "special"
    is an interpreter for special environment variables; for instance,
    a special may take the PATH environment variable and represent it
    as a list-like object.
    """

    @abc.abstractmethod
    def __init__(self, env, var):
        """
        Initialize a ``Special`` instance.  This is an abstract method
        with an implementation; subclasses must ensure that the
        superclass ``__init__()`` method is called.

        :param env: The environment the special is bound to.
        :type env: ``stepmaker.Environment``
        :param str var: The name of the environment variable the
                        special is bound to.
        """

        self._env = env
        self._var = var

    @abc.abstractmethod
    def set(self, value):
        """
        Set the value of a special.  This method is called when a value is
        assigned directly to the environment variable, and enables the
        special to perform any transformations to the value it
        requires.  The special is responsible for updating the value
        in the environment by calling the superclass ``set()`` method
        with a string value.

        :param value: The value to set.
        """

        self._env._set(self._var, value)

    @abc.abstractmethod
    def delete(self):
        """
        Delete the value of a special.  This method is called when a
        variable is deleted from the environment, and enables the
        special to perform any cache invalidation that it requires.
        The special is responsible for updating the value in the
        environment by calling the superclass ``delete()`` method.
        """

        self._env._delete(self._var)

    @property
    def raw(self):
        """
        Return the raw value of the underlying environment variable.
        """

        return self._env.get_raw(self._var)


class SpecialList(Special, collections.MutableSequence):
    """
    A special for list-like environment variables.  This splits the
    values on the system path separator (or, with the ``with_sep()``
    factory class method, on a specified separator) and presents a
    list-like view of the environment variable.
    """

    @classmethod
    def with_sep(cls, sep):
        """
        By default, the ``SpecialList`` special uses the system-specific
        path separator (often ':' on POSIX and ';' on Windows).  This
        factory class method allows an alternative separator to be
        used.

        :param str sep: The item separator to use.

        :returns: A factory function suitable for registering with an
                  ``Environment`` instance.
        """

        return functools.partial(cls, sep=sep)

    def __init__(self, env, var, sep=os.pathsep):
        """
        Initialize a ``SpecialList`` instance.

        :param env: The environment the special is bound to.
        :type env: ``stepmaker.Environment``
        :param str var: The name of the environment variable the
                        special is bound to.
        :param str sep: The item separator to use.  Defaults to the
                        system path separator.
        """

        # Initialize the superclass and store the separator
        super(SpecialList, self).__init__(env, var)
        self._sep = sep

        # Try to interpret the current value
        try:
            self._value = self.raw.split(self._sep)
        except KeyError:
            # Not set
            self._value = []

    def __repr__(self):
        """
        Return a suitable representation of the value.
        """

        return repr(self._value)

    def __len__(self):
        """
        Return the number of elements in the list.

        :returns: The number of elements in the list.
        :rtype: ``int``
        """

        return len(self._value)

    def __getitem__(self, idx):
        """
        Retrieve a specified item.

        :param idx: The index or slice.
        :type idx: ``int`` or ``slice``

        :returns: The specified item or items.
        :rtype: ``str`` or ``list`` of ``str``
        """

        return self._value[idx]

    def __setitem__(self, idx, value):
        """
        Set the value of a specified item.

        :param idx: The index or slice.
        :type idx: ``int`` or ``slice``
        :param value: The value to set.
        :type value: ``str`` or ``list`` of ``str``
        """

        self._value[idx] = value
        self._update()

    def __delitem__(self, idx):
        """
        Delete a specified item.

        :param idx: The index or slice.
        :type idx: ``int`` or ``slice``
        """

        del self._value[idx]
        self._update()

    def _update(self):
        """
        Update the value of the environment variable.
        """

        super(SpecialList, self).set(self._sep.join(self._value))

    def set(self, value):
        """
        Set the value of a special.  This method is called when a value is
        assigned directly to the environment variable, and enables the
        special to perform any transformations to the value it
        requires.  The special is responsible for updating the value
        in the environment by calling the superclass ``set()`` method
        with a string value.

        :param value: The value to set.
        """

        if isinstance(value, six.string_types):
            # Split strings
            self._value = value.split(self._sep)
        else:
            # Convert whatever it is to a list
            self._value = list(value)

        self._update()

    def delete(self):
        """
        Delete the value of a special.  This method is called when a
        variable is deleted from the environment, and enables the
        special to perform any cache invalidation that it requires.
        The special is responsible for updating the value in the
        environment by calling the superclass ``delete()`` method.
        """

        self._value = []
        super(SpecialList, self).delete()

    def insert(self, idx, value):
        """
        Insert an item into the list.

        :param int idx: The index at which to insert the value.
        :param str value: The value to insert.
        """

        self._value.insert(idx, value)
        self._update()


class SpecialSet(Special, collections.MutableSet):
    """
    A special for set-like environment variables.  This splits the
    values on the system path separator (or, with the ``with_sep()``
    factory class method, on a specified separator) and presents a
    set-like view of the environment variable.
    """

    @classmethod
    def with_sep(cls, sep):
        """
        By default, the ``SpecialSet`` special uses the system-specific
        path separator (often ':' on POSIX and ';' on Windows).  This
        factory class method allows an alternative separator to be
        used.

        :param str sep: The item separator to use.

        :returns: A factory function suitable for registering with an
                  ``Environment`` instance.
        """

        return functools.partial(cls, sep=sep)

    def __init__(self, env, var, sep=os.pathsep):
        """
        Initialize a ``SpecialSet`` instance.

        :param env: The environment the special is bound to.
        :type env: ``stepmaker.Environment``
        :param str var: The name of the environment variable the
                        special is bound to.
        :param str sep: The item separator to use.  Defaults to the
                        system path separator.
        """

        # Initialize the superclass and store the separator
        super(SpecialSet, self).__init__(env, var)
        self._sep = sep

        # Try to interpret the current value
        try:
            self._value = set(self.raw.split(self._sep))
        except KeyError:
            # Not set
            self._value = set()

    def __repr__(self):
        """
        Return a suitable representation of the value.
        """

        return repr(self._value)

    def __len__(self):
        """
        Return the number of elements in the set.

        :returns: The number of elements in the set.
        :rtype: ``int``
        """

        return len(self._value)

    def __iter__(self):
        """
        Iterate over the items in the set.

        :returns: An iterator over the items in the set.
        """

        return iter(self._value)

    def __contains__(self, item):
        """
        Determine if an item is contained within the set.

        :returns: A ``True`` value if the item is in the set,
                  ``False`` otherwise.
        """

        return item in self._value

    def _update(self):
        """
        Update the value of the environment variable.
        """

        super(SpecialSet, self).set(self._sep.join(sorted(self._value)))

    def set(self, value):
        """
        Set the value of a special.  This method is called when a value is
        assigned directly to the environment variable, and enables the
        special to perform any transformations to the value it
        requires.  The special is responsible for updating the value
        in the environment by calling the superclass ``set()`` method
        with a string value.

        :param value: The value to set.
        """

        if isinstance(value, six.string_types):
            # Split strings
            self._value = set(value.split(self._sep))
        else:
            # Convert whatever it is to a set
            self._value = set(value)

        self._update()

    def delete(self):
        """
        Delete the value of a special.  This method is called when a
        variable is deleted from the environment, and enables the
        special to perform any cache invalidation that it requires.
        The special is responsible for updating the value in the
        environment by calling the superclass ``delete()`` method.
        """

        self._value = set()
        super(SpecialSet, self).delete()

    def add(self, item):
        """
        Add an item to the set.

        :param str item: The item to add.
        """

        self._value.add(item)
        self._update()

    def discard(self, item):
        """
        Discard an item from the set.

        :param str item: The item to discard.
        """

        self._value.discard(item)
        self._update()


class SpecialDict(Special, collections.MutableMapping):
    """
    A special for dictionary-like environment variables.  This splits
    the values on the system path separator (or, with the
    ``with_sep()`` factory class method, on a specified item
    separator), then further splits the key from the value on the '='
    character (also settable with ``with_sep()``) and presents a
    dictionary-like view of the environment variable.
    """

    @classmethod
    def with_sep(cls, item_sep=os.pathsep, key_sep='='):
        """
        By default, the ``SpecialDict`` special uses the system-specific
        path separator (often ':' on POSIX and ';' on Windows) as the
        item separator, and '=' as the key-value separator.  This
        factory class method allows alternative separators to be used.

        :param str item_sep: The item separator to use.  Defaults to
                             the system path separator.
        :param str key_sep: The key-value separator to use.  Defaults
                            to '='.

        :returns: A factory function suitable for registering with an
                  ``Environment`` instance.
        """

        return functools.partial(cls, item_sep=item_sep, key_sep=key_sep)

    def __init__(self, env, var, item_sep=os.pathsep, key_sep='='):
        """
        Initialize a ``SpecialDict`` instance.

        :param env: The environment the special is bound to.
        :type env: ``stepmaker.Environment``
        :param str var: The name of the environment variable the
                        special is bound to.
        :param str item_sep: The item separator to use.  Defaults to
                             the system path separator.
        :param str key_sep: The key-value separator to use.  Defaults
                            to '='.
        """

        # Initialize the superclass and store the separators
        super(SpecialDict, self).__init__(env, var)
        self._item_sep = item_sep
        self._key_sep = key_sep

        # Try to interpret the current value
        try:
            self._value = self._split(self.raw)
        except KeyError:
            # Not set
            self._value = {}

    def __repr__(self):
        """
        Return a suitable representation of the value.
        """

        return repr(self._value)

    def __len__(self):
        """
        Return the number of elements in the dictionary.

        :returns: The number of elements in the dictionary.
        :rtype: ``int``
        """

        return len(self._value)

    def __iter__(self):
        """
        Iterate over the items in the dictionary.

        :returns: An iterator over the items in the dictionary.
        """

        return iter(self._value)

    def __getitem__(self, key):
        """
        Retrieve the value of a specified key.

        :param str key: The key to retrieve.

        :returns: The value of the specified key.
        :rtype: ``str``
        """

        return self._value[key]

    def __setitem__(self, key, value):
        """
        Sets the value of a specified key.

        :param str key: The key to set.
        :param str value: The value to set the key to.
        """

        self._value[key] = value
        self._update()

    def __delitem__(self, key):
        """
        Delete a specified key.

        :param str key: The key to delete.
        """

        del self._value[key]
        self._update()

    def _update(self):
        """
        Update the value of the environment variable.
        """

        super(SpecialDict, self).set(
            self._item_sep.join(
                '%s%s%s' % (
                    key,
                    '' if value is None else self._key_sep,
                    '' if value is None else value
                ) for key, value in
                sorted(self._value.items(), key=lambda x: x[0])
            )
        )

    def _split(self, value):
        """
        A helper routine to split item values.

        :param str value: The string value to split.

        :returns: A dictionary composed from the string value.  Note
                  that keys not followed by the key-value separator
                  will be set to the value ``None``.
        :rtype: ``dict`` mapping ``str`` to ``str`` or ``None``
        """

        result = {}
        for item in value.split(self._item_sep):
            key, sep, value = item.partition(self._key_sep)
            result[key] = value if sep else None
        return result

    def set(self, value):
        """
        Set the value of a special.  This method is called when a value is
        assigned directly to the environment variable, and enables the
        special to perform any transformations to the value it
        requires.  The special is responsible for updating the value
        in the environment by calling the superclass ``set()`` method
        with a string value.

        :param value: The value to set.
        """

        if isinstance(value, six.string_types):
            # Split strings
            self._value = self._split(value)
        else:
            # Convert whatever it is to a dict
            self._value = dict(value)

        self._update()

    def delete(self):
        """
        Delete the value of a special.  This method is called when a
        variable is deleted from the environment, and enables the
        special to perform any cache invalidation that it requires.
        The special is responsible for updating the value in the
        environment by calling the superclass ``delete()`` method.
        """

        self._value = {}
        super(SpecialDict, self).delete()


class SpecialOrderedDict(Special, collections.MutableMapping):
    """
    A special for OrderedDict-like environment variables.  This splits
    the values on the system path separator (or, with the
    ``with_sep()`` factory class method, on a specified item
    separator), then further splits the key from the value on the '='
    character (also settable with ``with_sep()``) and presents a
    dictionary-like view of the environment variable.
    """

    @classmethod
    def with_sep(cls, item_sep=os.pathsep, key_sep='='):
        """
        By default, the ``SpecialOrderedDict`` special uses the
        system-specific path separator (often ':' on POSIX and ';' on
        Windows) as the item separator, and '=' as the key-value
        separator.  This factory class method allows alternative
        separators to be used.

        :param str item_sep: The item separator to use.  Defaults to
                             the system path separator.
        :param str key_sep: The key-value separator to use.  Defaults
                            to '='.

        :returns: A factory function suitable for registering with an
                  ``Environment`` instance.
        """

        return functools.partial(cls, item_sep=item_sep, key_sep=key_sep)

    def __init__(self, env, var, item_sep=os.pathsep, key_sep='='):
        """
        Initialize a ``SpecialOrderedDict`` instance.

        :param env: The environment the special is bound to.
        :type env: ``stepmaker.Environment``
        :param str var: The name of the environment variable the
                        special is bound to.
        :param str item_sep: The item separator to use.  Defaults to
                             the system path separator.
        :param str key_sep: The key-value separator to use.  Defaults
                            to '='.
        """

        # Initialize the superclass and store the separators
        super(SpecialOrderedDict, self).__init__(env, var)
        self._item_sep = item_sep
        self._key_sep = key_sep

        # Try to interpret the current value
        try:
            self._value = self._split(self.raw)
        except KeyError:
            # Not set
            self._value = collections.OrderedDict()

    def __repr__(self):
        """
        Return a suitable representation of the value.
        """

        return repr(self._value)

    def __len__(self):
        """
        Return the number of elements in the dictionary.

        :returns: The number of elements in the dictionary.
        :rtype: ``int``
        """

        return len(self._value)

    def __iter__(self):
        """
        Iterate over the items in the dictionary.

        :returns: An iterator over the items in the dictionary.
        """

        return iter(self._value)

    def __getitem__(self, key):
        """
        Retrieve the value of a specified key.

        :param str key: The key to retrieve.

        :returns: The value of the specified key.
        :rtype: ``str``
        """

        return self._value[key]

    def __setitem__(self, key, value):
        """
        Sets the value of a specified key.

        :param str key: The key to set.
        :param str value: The value to set the key to.
        """

        self._value[key] = value
        self._update()

    def __delitem__(self, key):
        """
        Delete a specified key.

        :param str key: The key to delete.
        """

        del self._value[key]
        self._update()

    def _update(self):
        """
        Update the value of the environment variable.
        """

        super(SpecialOrderedDict, self).set(
            self._item_sep.join(
                '%s%s%s' % (
                    key,
                    '' if value is None else self._key_sep,
                    '' if value is None else value
                ) for key, value in self._value.items()
            )
        )

    def _split(self, value):
        """
        A helper routine to split item values.

        :param str value: The string value to split.

        :returns: A dictionary composed from the string value.  Note
                  that keys not followed by the key-value separator
                  will be set to the value ``None``.
        :rtype: ``dict`` mapping ``str`` to ``str`` or ``None``
        """

        result = collections.OrderedDict()
        for item in value.split(self._item_sep):
            key, sep, value = item.partition(self._key_sep)
            result[key] = value if sep else None
        return result

    def set(self, value):
        """
        Set the value of a special.  This method is called when a value is
        assigned directly to the environment variable, and enables the
        special to perform any transformations to the value it
        requires.  The special is responsible for updating the value
        in the environment by calling the superclass ``set()`` method
        with a string value.

        :param value: The value to set.
        """

        if isinstance(value, six.string_types):
            # Split strings
            self._value = self._split(value)
        elif isinstance(value, collections.OrderedDict):
            self._value = value.copy()
        else:
            # Convert whatever it is to an OrderedDict
            self._value = collections.OrderedDict(value)

        self._update()

    def delete(self):
        """
        Delete the value of a special.  This method is called when a
        variable is deleted from the environment, and enables the
        special to perform any cache invalidation that it requires.
        The special is responsible for updating the value in the
        environment by calling the superclass ``delete()`` method.
        """

        self._value = collections.OrderedDict()
        super(SpecialOrderedDict, self).delete()
