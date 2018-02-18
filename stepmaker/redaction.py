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

import six


@six.python_2_unicode_compatible
class Redacted(object):
    """
    Class for objects indicating key values that have been redacted.
    This is used in conjunction with the ``RedactedDict`` proxy class.
    """

    def __init__(self, text='<redacted>'):
        """
        Initialize a ``Redacted`` instance.

        :param str text: The text to output.  Defaults to
                         '<redacted>'.
        """

        self.text = text

    def __str__(self):
        """
        Retrieve a string representation of the object.

        :returns: The text that was passed to the constructor.
        :rtype: ``str``
        """

        return self.text


# Create a singleton for Redacted* classes to default to
redacted = Redacted()


class RedactedObject(object):
    """
    A proxy class for an object.  This proxies all attribute access to
    an underlying object, but allows certain attributes to be marked
    as "redacted"; attempts to obtain the values of those attributes
    will return a designated object to indicate that their values are
    redacted.
    """

    def __init__(self, obj, redacted_attrs=None, redacted=redacted):
        """
        Initialize a ``RedactedObject`` instance.

        :param obj: The object to proxy for.
        :param redacted_attrs: Attributes to mark redacted.  The set
                               passed here can be updated by processes
                               outside of the class.
        :type redacted_attrs: ``set`` of ``str``
        :param redacted: The object to return for redacted keys.
                         Defaults to the ``redacted`` singleton.
        :type redacted: ``Redacted``
        """

        self.__redacted_obj__ = obj
        self.__redacted_attrs__ = redacted_attrs or set()
        self.__redacted__ = redacted

    def __getattr__(self, name):
        """
        Retrieve an attribute from the proxied object.

        :param str name: The name of the attribute to retrieve.

        :returns: The value of the attribute.

        :raises AttributeError:
            The attribute does not exist on the proxied object.
        """

        # Proxy to the object; this allows the object to do whatever
        # it does with attribute access even if it's redacted, while
        # still allowing AttributeError to be raised
        value = getattr(self.__redacted_obj__, name)
        return self.__redacted__ if name in self.__redacted_attrs__ else value

    def __setattr__(self, name, value):
        """
        Set an attribute on the proxied object.

        :param str name: The name of the attribute to set.
        :param value: The value to set the attribute to.
        """

        # Is it one of our internal attributes?
        if name.startswith('__redacted_') and name.endswith('__'):
            super(RedactedObject, self).__setattr__(name, value)
        else:
            setattr(self.__redacted_obj__, name, value)

    def __delattr__(self, name):
        """
        Delete an attribute of the proxied object.

        :param str name: The name of the attribute to delete.

        :raises AttributeError:
            The attribute does not exist on the proxied object.
        """

        # Is it one of our internal attributes?
        if name.startswith('__redacted_') and name.endswith('__'):
            super(RedactedObject, self).__delattr__(name)
        else:
            delattr(self.__redacted_obj__, name)


class RedactedDict(RedactedObject, collections.MutableMapping):
    """
    A proxy class for a dictionary.  This proxies all attribute and
    item accesses to an underlying object, but allows certain keys to
    be marked as "redacted"; attempts to obtain the values of those
    keys will return a designated object to indicate that their values
    are redacted.
    """

    def __init__(self, obj, redacted_keys=None, redacted_attrs=None,
                 redacted=redacted):
        """
        Initialize a ``RedactedDict`` instance.

        :param obj: The dictionary or dictionary-like object to proxy
                    for.
        :param redacted_keys: Dictionary keys to mark redacted.  The
                              set passed here can be updated by
                              processes outside of the class.
        :type redacted_keys: ``set`` of ``str``
        :param redacted_attrs: Attributes to mark redacted.  The set
                               passed here can be updated by processes
                               outside of the class.
        :type redacted_attrs: ``set`` of ``str``
        :param redacted: The object to return for redacted keys.
                         Defaults to the ``redacted`` singleton.
        :type redacted: ``Redacted``
        """

        super(RedactedDict, self).__init__(obj, redacted_attrs, redacted)
        self.__redacted_keys__ = redacted_keys or set()

    def __len__(self):
        """
        Obtain the length of the proxied object.

        :returns: The length of the proxied object.
        :rtype: ``int``
        """

        return len(self.__redacted_obj__)

    def __iter__(self):
        """
        Iterate over the proxied object.

        :returns: An iterator over the proxied object.
        """

        return iter(self.__redacted_obj__)

    def __getitem__(self, name):
        """
        Retrieve an item from the proxied object.

        :param str name: The key to retrieve.

        :returns: The value of the key, or the ``redacted`` parameter
                  to the constructor if the key has been redacted.

        :raises KeyError:
            The key does not exist on the proxied object.
        """

        # Proxy to the object; this allows the object to magically
        # create the key even if it's redacted, while still allowing
        # KeyError to be raised
        value = self.__redacted_obj__[name]
        return self.__redacted__ if name in self.__redacted_keys__ else value

    def __setitem__(self, name, value):
        """
        Set an item on the proxied object.

        :param str name: The name of the item to set.
        :param value: The value to set the item to.
        """

        self.__redacted_obj__[name] = value

    def __delitem__(self, name):
        """
        Delete an item of the proxied object.

        :param str name: The name of the item to delete.

        :raises KeyError:
            The key does not exist on the proxied object.
        """

        del self.__redacted_obj__[name]


class Inverter(object):
    """
    An inverter for sets.  This contains only a ``__contains__()``
    method that returns the logical NOT of what the set contains.
    This allows the ``RedactedObject`` and ``RedactedDict`` classes to
    use white-list policies without additional code.
    """

    def __init__(self, base):
        """
        Initialize an ``Inverter`` instance.

        :param set base: The set to invert the sense of.
        """

        self._base = base

    def __contains__(self, item):
        """
        Determine if an item is a member of the underlying set.  This
        inverts the sense of the test, to allow for white-list
        policies with ``RedactedObject`` and ``RedactedDict``.

        :param item: The item to test for set membership.

        :returns: A ``False`` if the object is a member of the
                  underlying set, ``True`` otherwise.
        :rtype: ``bool``
        """

        return item not in self._base
