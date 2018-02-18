=================================
Step Maker Step-parsing Framework
=================================

.. image:: https://travis-ci.org/klmitch/stepmaker.svg?branch=master
    :target: https://travis-ci.org/klmitch/stepmaker

The `ansible`_ system automation tool uses, as its primary primitive,
a list of steps to execute, expressed in YAML list syntax.  Each step
is described as a dictionary, with one key indicating the actual
action to take, along with some additional keys that describe metadata
about the step (such as a description) or modifiers for the step (such
as conditional expressions).  This package provides a framework for
building applications that use similar step descriptions.

Steps
=====

As mentioned above, steps consist of metadata, modifiers, and an
action, all expressed through keys on the step dictionary.  The
``stepmaker`` package provides the abstract superclasses ``Step``,
``Modifier``, and ``Action`` that can be extended to provide
application-specific step structure.

The ``Step`` class is the main class for ``stepmaker``.  Implementors
must subclass ``Step`` and provide an implementation for the
``validate()`` method, as well as setting the ``namespace_actions``
and ``namespace_modifiers`` class variables.  The ``metadata_keys``
class variable can be used to identify particular keys as metadata.
The ``Step`` class provides a ``parse_list()`` class method for
parsing a list of dictionaries as step descriptions, using actions and
modifiers discovered in the entrypoint groups declared using
``namespace_actions`` and ``namespace_modifiers``.  Invoking the step
is as simple as calling the ``Step`` object with an
application-specific context.

The ``Action`` class is an abstract superclass for step actions.
Implementors must subclass ``Action`` and implement its ``validate()``
and ``__call__()`` methods.  The ``Action`` subclass performs the
actual work of the step.  Note that actions are classed as either
"eager" or "lazy", controlled by the ``eager`` class variable, with
the default being lazy.  Eager actions can be used to allow for
including other files or other libraries of step actions during
parsing by ``Step.parse_list()``.

The ``Modifier`` class is an abstract superclass for step modifiers.
A step modifier is able to modify how the action is performed;
everything from temporary mutations of the execution context to
skipping the step, or even executing the action multiple times (the
``Step.evaluate()`` method can facilitate this).  Implementors must
implement its ``validate()`` method, and then may implement the
``pre_call()`` and/or ``post_call()`` hook methods to perform the
necessary work.  Implementors may also set the ``restriction`` class
variable to restrict which actions a modifier can be used with; the
``before`` and ``after`` class variables provide control over the
order with which modifiers are applied; and the ``required`` and
``prohibited`` class variables can control which other modifiers are
required or prohibited on a given step.

For full details on defining steps, see the documentation on the
``Step``, ``Action``, and ``Modifier`` classes.

Utilities
=========

A number of utilities are also made available to assist with the
creation of a step-driven application.  For instance, the
``validate()`` methods of the ``Step``, ``Action``, and ``Modifier``
classes could be implemented using the ``jsonschema`` package; the
``jsonschema_validator()`` context manager can be used with
``jsonschema.validate()`` to translate schema validation errors into
more helpful ``StepError`` exceptions, which include the "address" of
a step configuration error.  The ``Environment`` class is a special
dictionary-like object containing system environment variables, but
also includes methods for registering "special" translators for
environment variables (e.g., the "PATH" environment variable could be
translated into a Python list-like object using the ``SpecialList``
translator), opening files relative to a working directory associated
with the ``Environment`` object, and even executing shell commands.
Finally, the ``RedactedObject`` and ``RedactedDict`` classes proxy to
other objects, but are additionally capable of masking certain
attributes or dictionary keys; this could be used on output routines
to ensure that sensitive data such as passwords is not exposed to the
console.

Modifiers
---------

Modifiers can inhibit the further processing of a step by raising the
``AbortStep`` exception from their ``pre_call()`` hook method.
Modifiers can also specify a result to be returned to the step's
caller by passing that result to ``AbortStep``.  If no result is
passed, the result will be the special singleton ``skipped``.

Note that ``post_call()`` processing of the modifier still occurs;
raising ``AbortStep`` prevents the processing of modifiers after the
one that raised it, but the ``post_call()`` method of the raising
modifier, along with the ones called before, are still called with the
result proposed in the ``AbortStep``.

Addresses and the Validator Methods
-----------------------------------

The ``StepAddress`` class is used to express the location of a
configuration item, and is used during parsing by ``Step.parse()`` and
``Step.parse_list()`` to raise helpful errors that indicate the
location of a configuration problem.  These addresses are also passed
on to actions and modifiers, and can be used by the ``validate()``
methods to raise appropriate ``StepError`` exceptions.  Additionally,
if using the ``jsonschema`` package for validation, the
``jsonschema_validator()`` context manager can be used to translate
schema validation errors raised by the package into ``StepError``
exceptions that include the address.  It can be used like so::

    with jsonschema_validator(addr):
        jsonschema.validate(config, schema)

(Note that ``jsonschema`` is *not* a dependency of ``stepmaker``.  The
``jsonschema_validator()`` function uses duck-typing to avoid needing
to install ``jsonschema`` alongside ``stepmaker``.)

Redacted Objects and Dictionaries
---------------------------------

Some data may be sensitive: an application developer may wish to
inhibit the display of that data to the console.  This data may be a
set of variables associated with the execution context, or it may even
be environment variables that may contain such things as passwords.
To ensure that such information cannot be accidentally displayed or
used, an implementor may choose to proxy an object or dictionary using
the ``RedactedObject`` and ``RedactedDict`` classes.  These classes
proxy attribute and, in the case of ``RedactedDict``, item accesses
back to an underlying object, but can return instances of ``Redacted``
for certain attributes or items.  By default, these classes return a
singleton ``redacted`` instance of ``Redacted``, which has a default
string representation of "<redacted>".

The attributes and items to redact are controlled by sets of attribute
names or item keys.  This implements a black-list policy, where only
certain attributes or items are redacted; to implement a white-list
policy, where all attributes or items are redacted except for
specified exceptions, wrap a set in the ``Inverter`` class; this will
invert the sense of membership tests.

It should be noted that the sets of attributes and items passed to
``RedactedObject`` and ``RedactedDict`` (and ``Inverter``) are saved
directly, and can be updated by processes outside of the classes.

Environment
-----------

Step-driven applications often need at least one step capable of
executing shell commands on the system, and also often need to be able
to manipulate environment variables and open files.  The ``stepmaker``
package provides an ``Environment`` class which provides all of this
functionality in a single object.  The class is a dictionary
containing the environment variables for execution of system commands
(note that this is distinct from the current contents of
``os.environ``, though the ``Environment`` class constructor uses the
current contents of ``os.environ`` as the default environment); the
class also keeps track of a current working directory (which is also
distinct from the process's current working directory).  Finally,
special interpreters can be associated with environment variables,
enabling, for instance, list-like access to the "PATH" environment
variable; a full collection of special interpreters is included, and
described below.

There are two ways to invoke a shell command using an ``Environment``
instance.  The first is to call ``popen()`` with a string or list
describing the command and its options, and a set of keyword arguments
suitable for passing to ``subprocess.Popen``.  This will return a
``subprocess.Popen`` instance, which may then be manipulated using the
methods provided by that class.  The second way to invoke a shell
command is to call the ``Environment``; the ``__call__()`` method is
similar to the ``subprocess.run()`` function provided in Python 3
versions of ``subprocess``, and will return a
``stepmaker.CompletedProcess`` object with the command's return code,
along with captured standard output and standard error (to capture
these streams, pass ``subprocess.PIPE`` or ``stepmaker.PIPE`` to the
``stdout`` and/or ``stderr`` keyword arguments to ``__call__()``).
Additionally, if the ``input`` keyword argument is provided, it will
be sent to the command's standard input; and if the ``check`` keyword
argument is set to ``True``, a ``stepmaker.ProcessError`` exception
will be raised if the command's return code is non-zero.  This will,
of course, wait for process execution to complete before continuing.

In addition to ``stepmaker.PIPE``, the ``stepmaker`` package also
copies ``subprocess.STDOUT`` for convenience.  This allows the use of
the ``Environment`` command execution facilities without having to
separately import ``subprocess``.

The ``Environment`` class tracks a working directory, which can be
changed by setting the ``cwd`` property.  Commands are, by default,
executed with there working directory set to the value of ``cwd``.  It
is also possible to locate a file relative to the ``cwd``, using the
``filename()`` method; and the file may even be opened (using the
``open()`` built-in) with the ``open()`` method.

Specials
~~~~~~~~

Specials are environment variable interpreters attached to an
``Environment`` instance.  They can be registered at construction
time, by passing keyword arguments of the form ``VARIABLE=factory``
(e.g., ``PATH=SpecialList``) to the constructor, or they can be
registered after the fact by calling the ``register()`` method of the
``Environment``.  (Specials may also be unregistered by calling
``register()`` without a factory function.)  Several specials are
provided, such as the ``SpecialList`` for list-like environment
variables, such as "PATH"; ``SpecialSet``, for set-like environment
variables (distinguished from list-like environment variables in that
ordering is not important); ``SpecialDict``, for dictionary-like
environment variables containing "key=value" pairs; or
``SpecialOrderedDict``, which is distinguished from ``SpecialDict`` by
the fact that it maintains the original key order.  The ``Special``
abstract base class can be used for constructing other specials.

It should be noted that the ``SpecialList``, ``SpecialSet``,
``SpecialDict``, and ``SpecialOrderedDict`` classes all contain a
``with_sep()`` class method that can be used to construct a factory
function using alternate separators.  If the default separators are
not suitable for a given application, then, instead of passing the
class as the factory function, pass the result of calling the class's
``with_sep()`` class method with appropriate arguments.

It should also be noted that ``Environment`` never deletes an instance
of a special unless a new special factory is registered (or the
special is deregistered).  This means that the value can be kept
outside of the environment.  In particular, it is possible to use a
``SpecialSet`` with a ``RedactedDict`` class wrapping the
``Environment``, so that environment variables to be redacted can be
listed in a particular environment variable.

.. _ansible: https://www.ansible.com/
