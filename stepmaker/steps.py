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
import sys

import entrypointer
import six

from stepmaker import exceptions
from stepmaker import utils


@six.add_metaclass(abc.ABCMeta)
class StepItem(object):
    """
    A superclass for all actions and modifiers.  This contains common
    pieces, such as config validation.
    """

    def __init__(self, name, config, addr):
        """
        Initialize the action or modifier.  This should process and store
        the configuration provided.  The default implementation stores
        the configuration as validated by the ``validate()`` method.

        :param str name: The name under which the action or modifier
                         was referenced.
        :param config: The configuration provided for the action or
                       modifier.
        :param addr: The address of the action or modifier.  This is
                     to be used when raising errors to help users
                     determine which action or modifier reported the
                     error.  Note that the actior or modifier ``name``
                     will already be included in the address.
        :type addr: ``stepmaker.StepAddress``
        """

        # Save the parameters
        self.name = name
        self.config = self.validate(name, config, addr)
        self.addr = addr

    @abc.abstractmethod
    def validate(self, name, config, addr):
        """
        Validate and canonicalize the configuration.  This method must be
        provided by subclasses, and is expected to report any errors.
        It must return the canonicalized form of the configuration.

        :param str name: The name under which the action or modifier
                         was referenced.
        :param config: The configuration provided for the action or
                       modifier.
        :param addr: The address of the action or modifier.  This is
                     to be used when raising errors to help users
                     determine which action or modifier reported the
                     error.  Note that the actior or modifier ``name``
                     will already be included in the address.
        :type addr: ``stepmaker.StepAddress``

        :returns: The canonicalized configuration.
        """

        pass  # pragma: no cover


class Action(StepItem):
    """
    A step *action*.  Actions are responsible for the actual operation
    performed by the test step.  Each step must have exactly one
    action.

    Actions may be either "lazy" or "eager".  Most actions are "lazy",
    meaning they are evaluated (by calling the ``__call__()`` method)
    after all steps have been read and parsed.  "Eager" actions are
    evaluated as soon as they are instantiated, and may be used for
    such things as "include" rules.  An action is "eager" if its
    ``eager`` class attribute is set to ``True``; it defaults to
    ``False``.
    """

    # Set to true to indicate an "eager" action
    eager = False

    @abc.abstractmethod
    def __call__(self, step, ctxt):
        """
        Evaluate the action.  Note that this method may be called multiple
        times, e.g., if there is a looping modifier in use, or it may
        not be called, e.g., if a conditional modifier inhibits
        evaluation.

        :param step: The step the action is in.
        :type step: ``Step``
        :param ctxt: An application-specific execution context.

        :returns: For "eager" actions, must return a list of ``Step``
                  instances.  For "lazy" actions, the return value is
                  application-specific.
        """

        pass  # pragma: no cover


class ModifierMeta(abc.ABCMeta):
    """
    A metaclass for the ``Modifier`` abstract base class.  This
    metaclass allows inheritance of the "before", "after", "required",
    and "prohibited" sets, which are used to ensure modifiers are
    processed in the correct order and that modifier
    cross-compatibility requirements are honored.
    """

    def __new__(mcs, name, bases, namespace):
        """
        Construct a new class.

        :param str name: The new class's name.
        :param tuple bases: A tuple of base classes.
        :param dict namespace: The namespace of the class being
                               constructed.
        """

        # Inherit the sets
        utils._inherit_set(
            ['before', 'after', 'required', 'prohibited'],
            bases,
            namespace,
        )

        # Construct the class
        return super(ModifierMeta, mcs).__new__(mcs, name, bases, namespace)


@six.add_metaclass(ModifierMeta)
class Modifier(StepItem):
    """
    A step *modifier*.  Modifiers modify a step in some fashion, such
    as through looping through a set of values for a step, or applying
    some condition.  They have hooks invoked both before and after a
    call to an action, and can inhibit execution of the action or
    later modifiers, or alter the action's return value in some
    fashion.

    Modifiers may be applied to either "lazy" or "eager" actions.
    This is controlled using the ``restriction`` attribute; if set to
    ``Modifier.LAZY``, the modifier only works with "lazy" actions,
    while if set to ``Modifier.EAGER``, the modifier only works with
    "eager" actions.  The ``restriction`` attribute may also be set to
    ``Modifier.ALL`` to indicate that it can be used with either
    "lazy" or "eager" actions.  The default is ``Modifier.ALL``.

    Modifiers have to be applied in some order.  By default, this
    ordering is lexical, by the modifier name, but a modifier may also
    hint that it should be applied before or after another modifier by
    including that modifier's name in the ``before`` or ``after``
    sets.  Note that these sets may be inherited from base
    classes--that is, if class A has ``before`` set to
    ``set(["m1"])``, and class B extends class A but has ``before``
    set to ``set(["m2"])`` in its definition, the actual value of
    ``before`` for the constructed class B will be set to ``set(["m1",
    "m2"])``.

    Modifiers can also specify that they must be used--or *must not*
    be used--with another modifier.  These restrictions are expressed
    through the ``required`` and ``prohibited`` sets, which exhibit a
    similar inheritance behavior as for the ``before`` and ``after``
    sets.

    Beyond the restriction to "lazy" or "eager" actions, there is no
    way to indicate that a modifier is incompatible with a given
    action.
    """

    # Constants for the restriction attribute
    LAZY = 0x01
    EAGER = 0x02
    ALL = LAZY | EAGER

    # Specify what types of actions the modifier may be used with
    restriction = ALL

    # Hint at modifier application ordering
    before = set()
    after = set()

    # Indicate modifier cross dependencies
    required = set()
    prohibited = set()

    def pre_call(self, step, ctxt, pre_mod, post_mod, action):
        """
        A modifier hook function.  These hooks are called in application
        order, prior to invoking the action.  They are passed lists of
        ``Modifier`` instances that have already been applied, as well
        as those that will be applied prior to calling the action.  To
        abort further step processing, raise a ``stepmaker.AbortStep``
        exception, optionally passing it a result.  Any other
        exception raised will also abort further step processing, with
        that exception becoming the result of the step.

        :param step: The step the modifier is in.
        :type step: ``Step``
        :param ctxt: An application-specific execution context.
        :param pre_mod: A list of the modifiers preceding this
                        modifier that have already been applied, in
                        the order in which they've been applied.
        :type pre_mod: ``list`` of ``Modifier``
        :param post_mod: A list of the modifiers not yet applied, in
                         the order in which they will be applied.
        :type post_mod: ``list`` of ``Modifier``
        :param action: The action to be invoked.
        :type action: ``Action``

        :raises stepmaker.AbortStep:
            If raised, step processing will be aborted, and the
            ``post_call()`` hooks of the modifiers in ``pre_mod`` will
            be executed in reverse order.  Any result passed to the
            ``stepmaker.AbortStep`` constructor will become the result
            of the step.
        """

        pass  # pragma: no cover

    def post_call(self, step, ctxt, result, action, post_mod, pre_mod):
        """
        A modifier hook function.  These hooks are called in reverse
        application order, after invoking the action.  They are passed
        lists of the ``Modifier`` instances applied to the action, in
        order of application, analogous to ``pre_call()``.  These
        hooks must return a result, which may be either the result
        that was passed in, or another result, depending on the
        purpose of the modifier.  If an exception is raised, that will
        become the result used for further processing, again, similar
        to ``pre_call()``.

        :param step: The step the modifier is in.
        :type step: ``Step``
        :param ctxt: An application-specific execution context.
        :param result: The result of the step, as returned by
                       ``action`` and modified by the modifiers in
                       ``post_mod``.
        :param action: The action that was invoked.
        :type action: ``Action``
        :param post_mod: A list of the modifiers whose ``post_mod()``
                         methods have been invoked.  This list is in
                         order of application, meaning that the first
                         modifier in the list was the modifier that
                         most recently handled the ``result``.
        :type post_mod: ``list`` of ``Modifier``
        :param pre_mod: A list of the modifiers whose ``post_mod()``
                        methods have not yet been invoked.  This list
                        is in order of application, meaning that the
                        last modifier in the list will be the next
                        modifier to handle the ``result``.
        :type pre_mod: ``list`` of ``Modifier``

        :returns: The result for further processing.  This may be
                  ``result``, or it may be another result.
        """

        return result


class StepMeta(abc.ABCMeta):
    """
    A metaclass for the ``Step`` abstract base class.  This metaclass
    allows inheritance of the "metadata_keys" set, which is used to
    identify step keys that represent metadata, rather than modifiers
    and actions.
    """

    def __new__(mcs, name, bases, namespace):
        """
        Construct a new class.

        :param str name: The new class's name.
        :param tuple bases: A tuple of base classes.
        :param dict namespace: The namespace of the class being
                               constructed.
        """

        # Inherit the metadata_keys set
        utils._inherit_set(['metadata_keys'], bases, namespace)

        # Construct the class
        return super(StepMeta, mcs).__new__(mcs, name, bases, namespace)


class ExceptionResult(object):
    """
    A wrapper for exceptions raised while processing a step.  The
    ``exc_info`` attribute contains the tuple of exception
    information, which may also be accessed using the ``type_``,
    ``value``, and ``traceback`` attributes.  The exception may be
    re-raised by calling the ``reraise()`` method.
    """

    def __init__(self, exc_info):
        """
        Initialize the ``ExceptionResult`` instance.

        :param exc_info: A tuple of exception information, as returned
                         by ``sys.exc_info()``.
        """

        self.exc_info = exc_info
        self.type_ = exc_info[0]
        self.value = exc_info[1]
        self.traceback = exc_info[2]

    def reraise(self):
        """
        Re-raise the wrapped exception.
        """

        six.reraise(*self.exc_info)


@six.add_metaclass(StepMeta)
class Step(object):
    """
    Represent a single step.  This class packages together step
    metadata, an action, and any modifiers into a single object, which
    becomes an entry in the list of steps.

    Metadata in a step description is differentiated from actions and
    modifiers using the ``metadata_keys`` set, which is subject to
    inheritance from base classes; that is, if class A has
    ``metadata_keys`` set to ``set(["mk1"])``, and class B extends
    class A but has ``metadata_keys`` set to ``set(["mk2"])`` in its
    definition, the actual value of ``metadata_keys`` for the
    constructed class B will be set to ``set(["mk1", "mk2"])``.

    Actions and modifiers are discovered using entrypoints; the
    entrypoint groups are specified by the ``namespace_actions`` and
    ``namespace_modifiers`` class attributes.  A typical way of
    setting these attributes is by appending '.actions' or
    '.modifiers' to a stem named after your application; for instance,
    if your application is called "myapp", ``namespace_actions`` may
    be set to "myapp.actions" while ``namespace_modifiers`` may be set
    to "myapp.modifiers".  Note that this is just a suggested naming
    scheme; the only restriction on these two values is that they must
    be distinct, in order to keep actions and modifiers separate.
    """

    # Keys constituting metadata
    metadata_keys = set()

    @abc.abstractproperty
    def namespace_actions(self):
        """
        The namespace to use to discover available actions.
        """

        pass  # pragma: no cover

    @abc.abstractproperty
    def namespace_modifiers(self):
        """
        The namespace to use to discover available modifiers.
        """

        pass  # pragma: no cover

    # Caches for the namespaces
    _group_acts = None
    _group_mods = None

    @classmethod
    def _get_action(cls, name, value, addr, action=None):
        """
        Helper for ``parse()`` to resolve an action.

        :param str name: The name of the action to resolve.
        :param value: The configuration value to pass on to the
                      action.
        :param addr: The address of the step.  This is to be used when
                     raising errors to help users determine which step
                     reported the error.
        :type addr: ``stepmaker.StepAddress``
        :param action: The currently set action.  If not ``None``,
                       this will be used to construct an error
                       message.

        :returns: A constructed action.
        :rtype: ``Action``

        :raises KeyError:
            An action with the given ``name`` does not exist.

        :raises stepmaker.StepError:
            The action has already been specified, or some other
            configuration error has been detected.
        """

        # Grab the _group_acts class attribute.  Using hasattr() keeps
        # the entrypoint group separate across multiple Step
        # subclasses.
        if cls._group_acts is None:
            cls._group_acts = getattr(entrypointer.eps, cls.namespace_actions)

        # Get the action class
        action_cls = cls._group_acts[name]

        # If there was already an action, complain about it
        if action is not None:
            raise exceptions.StepError(
                'Multiple actions "%s" and "%s" specified in step' %
                (name, action.name),
                addr,
            )

        # OK, return the instantiated action
        return action_cls(name, value, addr.key(name))

    @classmethod
    def _get_modifier(cls, name, value, addr, modifiers):
        """
        Helper for ``parse()`` to resolve a modifier.

        :paramstr name: The name of the modifier to resolve.
        :param value: The configuration value to pass on to the
                      modifier.
        :param addr: The address of the step.  This is to be used when
                     raising errors to help users determine which step
                     reported the error.
        :type addr: ``stepmaker.StepAddress``
        :param modifiers: A dictionary of modifiers.  This dictionary
                          will be updated with the new modifier
                          instance.
        :type modifiers: ``dict`` mapping ``str`` to ``Modifier``

        :raises KeyError:
            A modifier with the given ``name`` does not exist.

        :raises stepmaker.StepError:
            Some configuration error has been detected.
        """

        # Grab the _group_mods class attribute.  Using hasattr() keeps
        # the entrypoint group separate across multiple Step
        # subclasses.
        if cls._group_mods is None:
            cls._group_mods = getattr(
                entrypointer.eps, cls.namespace_modifiers
            )

        # Get the modifier class
        modifier_cls = cls._group_mods[name]

        # Add it to the modifiers dictionary
        modifiers[name] = modifier_cls(name, value, addr.key(name))

    @classmethod
    def parse(cls, description, addr):
        """
        Parse a step description.

        :param description: A description of the step.  A bare string
                            will be interpreted as a step having only
                            an action with configuration set to
                            ``None``.
        :type description: ``str``, or ``dict`` mapping ``str`` to
                           action- or modifier-specific configuration
        :param addr: The address of the step.  This is to be used when
                     raising errors to help users determine which step
                     reported the error.
        :type addr: ``stepmaker.StepAddress``

        :returns: A parsed step.
        :rtype: ``Step``
        """

        # Begin by normalizing the description
        if isinstance(description, six.string_types):
            # Short-circuit the dictionary processing logic
            return cls(cls._get_action(description, None, addr), addr)

        # Now split the dictionary up into metadata, action, and
        # modifier instances
        metadata = {}
        action = None
        modifiers = {}
        for key, value in description.items():
            # Handle metadata first
            if key in cls.metadata_keys:
                metadata[key] = value
                continue

            # OK, let's see if it's an action
            try:
                action = cls._get_action(key, value, addr, action)
            except KeyError:
                pass
            else:
                # This gets optimized out
                continue  # pragma: no cover

            # OK, must be a modifier
            try:
                cls._get_modifier(key, value, addr, modifiers)
            except KeyError:
                raise exceptions.StepError(
                    'Unknown action or modifier "%s"' % key,
                    addr,
                )

        # Make sure we have an action
        if action is None:
            raise exceptions.StepError('No action specified', addr)

        # Need to know the type of action and the modifier set
        action_type = Modifier.EAGER if action.eager else Modifier.LAZY
        modifier_set = set(modifiers)

        # Check that the modifiers are compatible
        for name, modifier in modifiers.items():
            # First, check for compatibility with the action
            if modifier.restriction & action_type == 0:
                raise exceptions.StepError(
                    'Modifier "%s" is incompatible with action "%s"' %
                    (modifier.name, action.name),
                    addr,
                )

            # Now check that prohibited modifiers aren't present
            prohibited = modifier_set & modifier.prohibited
            if prohibited:
                raise exceptions.StepError(
                    'Modifier "%s" cannot be used with modifier(s): "%s"' %
                    (modifier.name, '", "'.join(sorted(prohibited))),
                    addr,
                )

            # How about required modifiers?
            required = modifier.required - modifier_set
            if required:
                raise exceptions.StepError(
                    'Modifier "%s" requires the use of modifier(s): "%s"' %
                    (modifier.name, '", "'.join(sorted(required))),
                    addr,
                )

        # Construct the step
        return cls(action, addr, utils._sort_modifiers(modifiers), metadata)

    @classmethod
    def parse_list(cls, ctxt, description, addr):
        """
        Parse a list of step descriptions.  "Eager" steps will also be
        evaluated, and the results of those calls will be presumed to
        be a list of steps to include in the list.  (The "eager"
        attribute of steps in the returned list will not be checked;
        the caller must implement the "eager" behavior, possibly by
        recursively calling the ``parse_list()`` method.)

        :param ctxt: An application-specific execution context.  Will
                     be passed to "eager" steps.
        :param description: A description of the list of steps.
        :type description: ``list`` of ``dict`` or ``str``.
        :param addr: The address of the list of steps.  This is to be
                     used when raising errors to help users determine
                     which step reported the error.
        :type addr: ``stepmaker.StepAddress``

        :returns: A list of parsed steps.
        :rtype: ``list`` of ``Step``
        """

        # Assemble the step list
        steps = []
        for idx, step_desc in enumerate(description):
            # Parse the step
            step = cls.parse(step_desc, addr.idx(idx))

            # Is it eager?
            if step.eager:
                steps.extend(step(ctxt))
            else:
                steps.append(step)

        return steps

    def __init__(self, action, addr, modifiers=None, metadata=None):
        """
        Initialize the step.  This should process and store the action and
        modifiers, in addition to other metadata.  The default
        implementation stores the metadata as validated by the
        ``validate()`` method.

        :param action: The step action.
        :type action: ``Action``
        :param addr: The address of the step.  This is to be used when
                     raising errors to help users determine which step
                     reported the error.
        :type addr: ``stepmaker.StepAddress``
        :param modifiers: Optional list of modifiers to apply to the
                          action.
        :type modifiers: ``list`` of ``Modifier``
        :param dict metadata: An optional dictionary of metadata
                              items.
        """

        # Save the parameters
        self.action = action
        self.addr = addr
        self.modifiers = modifiers or []
        self.metadata = self.validate(metadata or {}, addr)

    def __call__(self, ctxt):
        """
        Evaluate the step.  Any exceptions raised by the action or a
        modifier will be wrapped in a ``stepmaker.ExceptionResult``
        and passed to the ``post_call()`` hook of the applied
        modifiers, and if the final result is still a
        ``stepmaker.ExceptionResult``, the exception will be
        re-raised.

        :param ctxt: An application-specific execution context.

        :returns: The result of evaluating the action, as modified by
                  any modifiers.  If processing was aborted by a
                  modifier, without specifying a return value, the
                  singleton ``stepmaker.skipped`` will be returned.
        """

        result = self.evaluate(ctxt, [], self.modifiers, self.action)

        # If the result was an exception, re-raise it
        if isinstance(result, ExceptionResult):
            result.reraise()

        return result

    def evaluate(self, ctxt, pre_call, post_call, action):
        """
        Core evaluation routine.  This is broken out as a public method to
        assist modifiers that need to directly evaluate remaining
        modifiers and the action, such as those modifiers that
        implement looping.  Any exceptions raised by the action or a
        modifier will be wrapped in a ``stepmaker.ExceptionResult``
        and passed to the ``post_call()`` hook of the applied
        modifiers.  The exception will not be re-raised, unlike with
        the ``__call__()`` method.

        :param ctxt: An application-specific execution context.
        :param pre_call: The list of modifiers that have already been
                         applied.  This is present simply to provide
                         the appropriate information to modifier hook
                         calls.
        :type pre_call: ``list`` of ``Modifier``
        :param post_call: The list of modifiers that have not yet been
                          applied.  This method will apply those
                          modifiers.
        :type post_call: ``list`` of ``Modifier``
        :param action: The action to invoke.
        :type action: ``Action``

        :returns: The result of evaluating the modifiers and action.
        """

        # Begin by walking the modifier list
        i = -1
        try:
            for i in range(len(post_call)):
                post_call[i].pre_call(
                    self,
                    ctxt,
                    pre_call + post_call[:i],
                    post_call[i + 1:],
                    action,
                )
        except exceptions.AbortStep as exc:
            # Step aborted
            result = exc.result
        except Exception:
            # An exception occurred while processing
            result = ExceptionResult(sys.exc_info())
        else:
            try:
                # Call the action
                result = action(self, ctxt)
            except Exception:
                # An exception occurred while processing
                result = ExceptionResult(sys.exc_info())

        # We've now evaluated all the pre_call's and the action, or
        # been aborted somewhere; now to call all the post_call hooks
        for j in range(i, -1, -1):
            try:
                result = post_call[j].post_call(
                    self,
                    ctxt,
                    result,
                    action,
                    post_call[j + 1:],
                    pre_call + post_call[:j],
                )
            except Exception:
                # An exception occurred while processing
                result = ExceptionResult(sys.exc_info())

        # Return the result of evaluation
        return result

    @abc.abstractmethod
    def validate(self, metadata, addr):
        """
        Validate and canonicalize the metadata.  This method must be
        provided by subclasses, and is expected to report any errors.
        It must return the canonicalized form of the metadata.

        :param dict metadata: The metadata to be validated.
        :param addr: The address of the step.  This is to be used when
                     raising errors to help users determine which step
                     reported the error.
        :type addr: ``stepmaker.StepAddress``

        :returns: The canonicalized metadata.
        """

        pass  # pragma: no cover

    @property
    def eager(self):
        """
        Indicate if the step is "eager".  A step is "eager" when its
        action is.
        """

        return self.action.eager
