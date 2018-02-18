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
import contextlib
import os

import six

from stepmaker import exceptions


def _canonicalize_path(cwd, path):
    """
    Canonicalizes a path relative to a given working directory.  That
    is, if the path is not absolute, it is interpreted relative to the
    specified working directory, then converted to absolute form.

    :param str cwd: The working directory.
    :param str path: The path to canonicalize.

    :returns: The absolute path.
    :rtype: ``str``
    """

    if not os.path.isabs(path):
        path = os.path.join(cwd, path)

    return os.path.abspath(path)


def _inherit_set(attrs, bases, namespace):
    """
    Helper for metaclasses.  This is used to allow inheritance of data
    from ``set`` attributes in a class; e.g., if a class declaration
    has an attribute set to ``set(['a', 'b'])``, and a superclass has
    the same attribute set to ``set(['b', 'c'])``, the final class
    will have that attribute set to ``set(['a', 'b', 'c'])``.

    :param attrs: A list of attribute names.
    :type attrs: ``list`` of ``str``
    :param tuple bases: A tuple of base classes.
    :param dict namespace: The namespace of the class being
                           constructed.  This will be updated in
                           place.
    """

    for attr in attrs:
        # Get the attribute value from the class namespace
        result = set(namespace.get(attr, []))

        # Add the results from all the base classes
        for base in bases:
            result |= getattr(base, attr, set())

        # Update the value in the namespace
        namespace[attr] = result


VisitQueueElem = collections.namedtuple('VisitQueueElem', ['mod', 'before'])


def _sort_visit(adjacency, result, node):
    """
    Perform the depth-first search starting at a given node.  This is
    the core of the topological sort algorithm used by
    ``_sort_modifiers()``.

    :param adjacency: The adjacency dictionary assembled by
                      ``_sort_modifiers()``.
    :param result: The result list to add modifiers to.
    :type result: ``list`` of ``stepmaker.Modifier``
    :param node: A node popped off the adjacency dictionary.
    """

    # Work queue
    queue = [
        VisitQueueElem(
            node['mod'],
            iter(sorted(node['before'], reverse=True)),
        ),
    ]

    # While there's work in the queue...
    while queue:
        try:
            # Get the next node that should be before this one
            vname = six.next(queue[-1].before)
            if vname in adjacency:
                # Pop that node off the adjacency list and add it to
                # the queue
                nextnode = adjacency.pop(vname)
                queue.append(VisitQueueElem(
                    nextnode['mod'],
                    iter(sorted(nextnode['before'], reverse=True)),
                ))
        except StopIteration:
            # Explored all its dependencies, add it to the results
            result.append(queue.pop().mod)


def _sort_modifiers(modifiers):
    """
    Perform a topological sort of the modifiers, based on their
    ``before`` and ``after`` attributes.

    :param modifiers: A dictionary mapping modifier names to
                      modifiers.
    :type modifiers: ``dict`` mapping ``str`` to ``Modifier``

    :returns: A list of modifiers in the proper order.
    :rtype: ``list`` of ``Modifier``
    """

    # First, build an adjacency map reduced to the set of nodes we
    # actually have
    adjacency = collections.defaultdict(lambda: {'before': set()})
    for name, modifier in modifiers.items():
        # Store the modifier
        adjacency[name]['mod'] = modifier

        # Include the modifier's before list
        adjacency[name]['before'] |= {
            oname for oname in modifier.before if oname in modifiers
        }

        # Now process the modifier's after list
        for oname in modifier.after:
            if oname not in modifiers:
                # Not one in the set of modifiers
                continue

            adjacency[oname]['before'].add(name)

    # Construct the result list and call our visitor
    result = []
    for vname in sorted(adjacency, reverse=True):
        # Only consider nodes still in the adjacency map
        if vname in adjacency:
            _sort_visit(adjacency, result, adjacency.pop(vname))

    # Return the reversed result
    result.reverse()
    return result


@contextlib.contextmanager
def jsonschema_validator(addr):
    """
    Helper for configuration validation using the ``jsonschema``
    package.  This function is a context manager that is passed the
    root address; if a ``jsonschema.ValidationError`` is raised by the
    encompassed code, it will be translated into a
    ``stepmaker.StepError`` exception with the proper address.  This
    function is written such that no direct dependency on the
    ``jsonschema`` package is created.

    :param addr: The address of the configuration being validated.
    :type addr: ``stepmaker.StepAddress``

    :returns: A context manager.
    """

    try:
        yield
    except Exception as exc:
        # Differentiate ValidationError by looking for a path
        # attribute with a sequence in it
        if (not hasattr(exc, 'path') or
                not isinstance(exc.path, collections.Sequence)):
            raise

        # OK, it has a path; assemble the path string fragment
        path = ''.join(
            ('/%s' if isinstance(elem, six.string_types) else '[%d]') % elem
            for elem in exc.path
        )

        # Raise it as a StepError
        raise exceptions.StepError(
            six.text_type(exc),
            addr.__class__(addr.filename, addr.path + path),
        )
