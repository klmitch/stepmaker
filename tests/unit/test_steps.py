import inspect
import sys

import pytest

from stepmaker import addresses
from stepmaker import exceptions
from stepmaker import steps


class ExceptionForTest(Exception):
    pass


class StepItemForTest(steps.StepItem):
    def validate(self, name, config, addr):
        pass


class TestStepItem(object):
    def test_init(self, mocker):
        mock_validate = mocker.patch.object(
            StepItemForTest, 'validate',
        )

        result = StepItemForTest('name', 'config', 'addr')

        assert result.name == 'name'
        assert result.config == mock_validate.return_value
        assert result.addr == 'addr'
        mock_validate.assert_called_once_with('name', 'config', 'addr')


class BaseA(object):
    pass


class BaseB(object):
    pass


class BaseC(object):
    pass


class TestModifierMeta(object):
    def test_new(self, mocker):
        mock_inherit_set = mocker.patch.object(
            steps.utils, '_inherit_set',
        )

        result = steps.ModifierMeta(
            'name',
            (BaseA, BaseB, BaseC),
            {'a': 1, 'b': 2},
        )

        assert inspect.isclass(result)
        mock_inherit_set.assert_called_once_with(
            ['before', 'after', 'required', 'prohibited'],
            (BaseA, BaseB, BaseC),
            {'a': 1, 'b': 2},
        )


class ModifierForTest(steps.Modifier):
    def validate(self, name, config, addr):
        return config


class TestModifier(object):
    def test_post_call(self):
        obj = ModifierForTest('name', 'config', 'addr')

        result = obj.post_call(
            'step', 'ctxt', 'result', 'pre_mod', 'post_mod', 'action',
        )

        assert result == 'result'


class TestStepMeta(object):
    def test_new(self, mocker):
        mock_inherit_set = mocker.patch.object(
            steps.utils, '_inherit_set',
        )

        result = steps.StepMeta(
            'name',
            (BaseA, BaseB, BaseC),
            {'a': 1, 'b': 2},
        )

        assert inspect.isclass(result)
        mock_inherit_set.assert_called_once_with(
            ['metadata_keys'], (BaseA, BaseB, BaseC), {'a': 1, 'b': 2},
        )


class TestExceptionResult(object):
    def test_init(self):
        exc_info = ('type', 'value', 'traceback')

        result = steps.ExceptionResult(exc_info)

        assert result.exc_info == exc_info
        assert result.type_ == 'type'
        assert result.value == 'value'
        assert result.traceback == 'traceback'

    def test_reraise(self, mocker):
        mock_reraise = mocker.patch.object(
            steps.six, 'reraise',
        )
        exc_info = ('type', 'value', 'traceback')
        obj = steps.ExceptionResult(exc_info)

        obj.reraise()

        mock_reraise.assert_called_once_with('type', 'value', 'traceback')


class StepForTest(steps.Step):
    metadata_keys = set(['meta1', 'meta2'])
    namespace_actions = 'stepmaker.actions'
    namespace_modifiers = 'stepmaker.modifiers'

    def validate(self, metadata, addr):
        return metadata


class TestStep(object):
    def test_get_action_cached(self, mocker):
        klass = mocker.Mock(return_value='action')
        cached = mocker.Mock(return_value='cached')
        mocker.patch.object(
            steps.entrypointer.eps, 'stepmaker.actions', {'test': klass},
        )
        mocker.patch.object(
            StepForTest, '_group_acts', {'test': cached},
        )
        addr = addresses.StepAddress('file.name', '/some/path')

        result = StepForTest._get_action('test', 'value', addr)

        assert result == 'cached'
        assert StepForTest._group_acts == {'test': cached}
        klass.assert_not_called()
        cached.assert_called_once_with('test', 'value', mocker.ANY)
        other_addr = cached.call_args[0][-1]
        assert isinstance(other_addr, addresses.StepAddress)
        assert id(other_addr) != id(addr)
        assert other_addr.filename == addr.filename
        assert other_addr.path == '/some/path/test'

    def test_get_action_uncached(self, mocker):
        klass = mocker.Mock(return_value='action')
        mocker.patch.object(
            steps.entrypointer.eps, 'stepmaker.actions', {'test': klass},
        )
        mocker.patch.object(
            StepForTest, '_group_acts', None,
        )
        addr = addresses.StepAddress('file.name', '/some/path')

        result = StepForTest._get_action('test', 'value', addr)

        assert result == 'action'
        assert StepForTest._group_acts == {'test': klass}
        klass.assert_called_once_with('test', 'value', mocker.ANY)
        other_addr = klass.call_args[0][-1]
        assert isinstance(other_addr, addresses.StepAddress)
        assert id(other_addr) != id(addr)
        assert other_addr.filename == addr.filename
        assert other_addr.path == '/some/path/test'

    def test_get_action_set(self, mocker):
        klass = mocker.Mock(return_value='action')
        mocker.patch.object(
            steps.entrypointer.eps, 'stepmaker.actions', {'test': klass},
        )
        mocker.patch.object(
            StepForTest, '_group_acts', None,
        )
        addr = addresses.StepAddress('file.name', '/some/path')
        action = mocker.Mock()
        action.name = 'spam'

        with pytest.raises(exceptions.StepError) as exc_info:
            StepForTest._get_action('test', 'value', addr, action)
        assert StepForTest._group_acts == {'test': klass}
        klass.assert_not_called()
        other_addr = exc_info.value.addr
        assert other_addr is addr

    def test_get_modifier_cached(self, mocker):
        klass = mocker.Mock(return_value='modifier')
        cached = mocker.Mock(return_value='cached')
        mocker.patch.object(
            steps.entrypointer.eps, 'stepmaker.modifiers', {'test': klass},
        )
        mocker.patch.object(
            StepForTest, '_group_mods', {'test': cached},
        )
        addr = addresses.StepAddress('file.name', '/some/path')
        mod_map = {
            'mod1': 'modifier1',
            'mod2': 'modifier2',
        }

        StepForTest._get_modifier('test', 'value', addr, mod_map)

        assert mod_map == {
            'mod1': 'modifier1',
            'mod2': 'modifier2',
            'test': 'cached',
        }
        assert StepForTest._group_mods == {'test': cached}
        klass.assert_not_called()
        cached.assert_called_once_with('test', 'value', mocker.ANY)
        other_addr = cached.call_args[0][-1]
        assert isinstance(other_addr, addresses.StepAddress)
        assert id(other_addr) != id(addr)
        assert other_addr.filename == addr.filename
        assert other_addr.path == '/some/path/test'

    def test_get_modifier_uncached(self, mocker):
        klass = mocker.Mock(return_value='modifier')
        mocker.patch.object(
            steps.entrypointer.eps, 'stepmaker.modifiers', {'test': klass},
        )
        mocker.patch.object(
            StepForTest, '_group_mods', None,
        )
        addr = addresses.StepAddress('file.name', '/some/path')
        mod_map = {
            'mod1': 'modifier1',
            'mod2': 'modifier2',
        }

        StepForTest._get_modifier('test', 'value', addr, mod_map)

        assert mod_map == {
            'mod1': 'modifier1',
            'mod2': 'modifier2',
            'test': 'modifier',
        }
        assert StepForTest._group_mods == {'test': klass}
        klass.assert_called_once_with('test', 'value', mocker.ANY)
        other_addr = klass.call_args[0][-1]
        assert isinstance(other_addr, addresses.StepAddress)
        assert id(other_addr) != id(addr)
        assert other_addr.filename == addr.filename
        assert other_addr.path == '/some/path/test'

    def test_parse_short_circuit(self, mocker):
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            return_value='action',
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )

        result = StepForTest.parse('test', 'addr')

        assert isinstance(result, StepForTest)
        mock_get_action.assert_called_once_with('test', None, 'addr')
        mock_get_modifier.assert_not_called()
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_called_once_with('action', 'addr')

    def test_parse_base(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=False),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'test': 'action config',
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        result = StepForTest.parse(config, 'addr')

        assert isinstance(result, StepForTest)
        mock_get_action.assert_has_calls([
            mocker.call('test', 'action config', 'addr', None),
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_action.call_count == 4
        mock_get_modifier.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_modifier.call_count == 3
        mock_sort_modifiers.assert_called_once_with(modifiers_map)
        mock_init.assert_called_once_with(
            actions_map['test'], 'addr', 'sorted', {
                'meta1': 'metadata 1',
                'meta2': 'metadata 2',
            },
        )

    def test_parse_missing_modifier(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=False),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'test': 'action config',
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'mod4': 'mod4 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        with pytest.raises(exceptions.StepError):
            StepForTest.parse(config, 'addr')
        # Dict ordering controls whether _get_action() gets called on
        # anything, so don't even check; also controls whether
        # _get_modifier() gets called on everything, so just check the
        # case that should fail
        mock_get_modifier.assert_has_calls([
            mocker.call('mod4', 'mod4 config', 'addr', mocker.ANY),
        ], any_order=True)
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_not_called()

    def test_parse_missing_action(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=False),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        with pytest.raises(exceptions.StepError):
            StepForTest.parse(config, 'addr')
        mock_get_action.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_action.call_count == 3
        mock_get_modifier.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_modifier.call_count == 3
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_not_called()

    def test_parse_lazy_only_modifier(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=True),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.LAZY,
                prohibited=set(), required=set(),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'test': 'action config',
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        with pytest.raises(exceptions.StepError):
            StepForTest.parse(config, 'addr')
        mock_get_action.assert_has_calls([
            mocker.call('test', 'action config', 'addr', None),
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_action.call_count == 4
        mock_get_modifier.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_modifier.call_count == 3
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_not_called()

    def test_parse_eager_only_modifier(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=False),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.EAGER,
                prohibited=set(), required=set(),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'test': 'action config',
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        with pytest.raises(exceptions.StepError):
            StepForTest.parse(config, 'addr')
        mock_get_action.assert_has_calls([
            mocker.call('test', 'action config', 'addr', None),
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_action.call_count == 4
        mock_get_modifier.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_modifier.call_count == 3
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_not_called()

    def test_parse_prohibited_modifier(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=False),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(['mod3']), required=set(),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'test': 'action config',
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        with pytest.raises(exceptions.StepError):
            StepForTest.parse(config, 'addr')
        mock_get_action.assert_has_calls([
            mocker.call('test', 'action config', 'addr', None),
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_action.call_count == 4
        mock_get_modifier.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_modifier.call_count == 3
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_not_called()

    def test_parse_required_modifier(self, mocker):
        def fake_get_modifier(name, value, addr, modifiers):
            modifiers[name] = modifiers_map[name]
        actions_map = {
            'test': mocker.Mock(eager=False),
        }
        for name, action in actions_map.items():
            action.name = name
        modifiers_map = {
            'mod1': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
            'mod2': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(['mod4']),
            ),
            'mod3': mocker.Mock(
                restriction=steps.Modifier.ALL,
                prohibited=set(), required=set(),
            ),
        }
        for name, modifier in modifiers_map.items():
            modifier.name = name
        mock_get_action = mocker.patch.object(
            StepForTest, '_get_action',
            side_effect=lambda name, value, addr, action: actions_map[name],
        )
        mock_get_modifier = mocker.patch.object(
            StepForTest, '_get_modifier',
            side_effect=fake_get_modifier,
        )
        mock_sort_modifiers = mocker.patch.object(
            steps.utils, '_sort_modifiers',
            return_value='sorted',
        )
        mock_init = mocker.patch.object(
            StepForTest, '__init__',
            return_value=None,
        )
        config = {
            'test': 'action config',
            'mod1': 'mod1 config',
            'mod2': 'mod2 config',
            'mod3': 'mod3 config',
            'meta1': 'metadata 1',
            'meta2': 'metadata 2',
        }

        with pytest.raises(exceptions.StepError):
            StepForTest.parse(config, 'addr')
        mock_get_action.assert_has_calls([
            mocker.call('test', 'action config', 'addr', None),
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_action.call_count == 4
        mock_get_modifier.assert_has_calls([
            mocker.call('mod1', 'mod1 config', 'addr', mocker.ANY),
            mocker.call('mod2', 'mod2 config', 'addr', mocker.ANY),
            mocker.call('mod3', 'mod3 config', 'addr', mocker.ANY),
        ], any_order=True)
        assert mock_get_modifier.call_count == 3
        mock_sort_modifiers.assert_not_called()
        mock_init.assert_not_called()

    def test_parse_list(self, mocker):
        steps = [
            mocker.Mock(eager=False, return_value='step1'),
            mocker.Mock(eager=False, return_value='step2'),
            mocker.Mock(eager=True, return_value=['step3', 'step4']),
            mocker.Mock(eager=False, return_value='step5'),
        ]
        mock_parse = mocker.patch.object(
            StepForTest, 'parse',
            side_effect=steps[:],
        )
        addr = addresses.StepAddress('file.name', '/some/path')
        description = ['conf1', 'conf2', 'conf3', 'conf5']

        result = StepForTest.parse_list('ctxt', description, addr)

        assert result == [steps[0], steps[1], 'step3', 'step4', steps[3]]
        mock_parse.assert_has_calls([
            mocker.call(conf, mocker.ANY) for conf in description
        ])
        assert mock_parse.call_count == len(description)
        for i in range(len(description)):
            tmp_addr = mock_parse.call_args_list[i][0][-1]
            assert isinstance(tmp_addr, addresses.StepAddress)
            assert id(tmp_addr) != id(addr)
            assert tmp_addr.filename == addr.filename
            assert tmp_addr.path == '/some/path[%d]' % i

    def test_init_base(self, mocker):
        mock_validate = mocker.patch.object(
            StepForTest, 'validate',
            return_value='validated',
        )

        result = StepForTest('action', 'addr')

        assert result.action == 'action'
        assert result.addr == 'addr'
        assert result.modifiers == []
        assert result.metadata == 'validated'
        mock_validate.assert_called_once_with({}, 'addr')

    def test_init_alt(self, mocker):
        mock_validate = mocker.patch.object(
            StepForTest, 'validate',
            return_value='validated'
        )

        result = StepForTest('action', 'addr', 'modifiers', 'metadata')

        assert result.action == 'action'
        assert result.addr == 'addr'
        assert result.modifiers == 'modifiers'
        assert result.metadata == 'validated'
        mock_validate.assert_called_once_with('metadata', 'addr')

    def test_call_base(self, mocker):
        mock_evaluate = mocker.patch.object(
            StepForTest, 'evaluate',
            return_value='result',
        )
        obj = StepForTest('action', 'addr', 'modifiers', 'metadata')

        result = obj('ctxt')

        assert result == 'result'
        mock_evaluate.assert_called_once_with(
            'ctxt', [], 'modifiers', 'action',
        )

    def test_call_exception(self, mocker):
        try:
            raise ExceptionForTest('haha!')
        except Exception:
            exc = steps.ExceptionResult(sys.exc_info())
        mock_evaluate = mocker.patch.object(
            StepForTest, 'evaluate',
            return_value=exc,
        )
        obj = StepForTest('action', 'addr', 'modifiers', 'metadata')

        with pytest.raises(ExceptionForTest) as exc_info:
            obj('ctxt')
        assert exc_info.type == exc.type_
        assert exc_info.value == exc.value
        mock_evaluate.assert_called_once_with(
            'ctxt', [], 'modifiers', 'action',
        )

    def test_evaluate_base(self, mocker):
        modifiers = [
            mocker.Mock(**{'post_call.return_value': 'mod%d' % i})
            for i in range(5)
        ]
        action = mocker.Mock(return_value='action')
        obj = StepForTest('action', 'addr', 'modifiers')

        result = obj.evaluate('ctxt', modifiers[:2], modifiers[2:], action)

        assert result == 'mod2'
        modifiers[0].pre_call.assert_not_called()
        modifiers[1].pre_call.assert_not_called()
        modifiers[2].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:2], modifiers[3:], action,
        )
        modifiers[3].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:3], modifiers[4:], action,
        )
        modifiers[4].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:4], modifiers[5:], action,
        )
        action.assert_called_once_with(obj, 'ctxt')
        modifiers[4].post_call.assert_called_once_with(
            obj, 'ctxt', 'action', action, modifiers[5:], modifiers[:4],
        )
        modifiers[3].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod4', action, modifiers[4:], modifiers[:3],
        )
        modifiers[2].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod3', action, modifiers[3:], modifiers[:2],
        )
        modifiers[1].post_call.assert_not_called()
        modifiers[0].post_call.assert_not_called()

    def test_evaluate_skipped(self, mocker):
        modifiers = [
            mocker.Mock(**{'post_call.return_value': 'mod%d' % i})
            for i in range(5)
        ]
        modifiers[3].pre_call.side_effect = exceptions.AbortStep()
        action = mocker.Mock(return_value='action')
        obj = StepForTest('action', 'addr', 'modifiers')

        result = obj.evaluate('ctxt', modifiers[:2], modifiers[2:], action)

        assert result == 'mod2'
        modifiers[0].pre_call.assert_not_called()
        modifiers[1].pre_call.assert_not_called()
        modifiers[2].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:2], modifiers[3:], action,
        )
        modifiers[3].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:3], modifiers[4:], action,
        )
        modifiers[4].pre_call.assert_not_called()
        action.assert_not_called()
        modifiers[4].post_call.assert_not_called()
        modifiers[3].post_call.assert_called_once_with(
            obj, 'ctxt', exceptions.skipped, action, modifiers[4:],
            modifiers[:3],
        )
        modifiers[2].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod3', action, modifiers[3:], modifiers[:2],
        )
        modifiers[1].post_call.assert_not_called()
        modifiers[0].post_call.assert_not_called()

    def test_evaluate_pre_call_fails(self, mocker):
        modifiers = [
            mocker.Mock(**{'post_call.return_value': 'mod%d' % i})
            for i in range(5)
        ]
        modifiers[3].pre_call.side_effect = ExceptionForTest('test')
        action = mocker.Mock(return_value='action')
        obj = StepForTest('action', 'addr', 'modifiers')

        result = obj.evaluate('ctxt', modifiers[:2], modifiers[2:], action)

        assert result == 'mod2'
        modifiers[0].pre_call.assert_not_called()
        modifiers[1].pre_call.assert_not_called()
        modifiers[2].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:2], modifiers[3:], action,
        )
        modifiers[3].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:3], modifiers[4:], action,
        )
        modifiers[4].pre_call.assert_not_called()
        action.assert_not_called()
        modifiers[4].post_call.assert_not_called()
        modifiers[3].post_call.assert_called_once_with(
            obj, 'ctxt', mocker.ANY, action, modifiers[4:], modifiers[:3],
        )
        exc_res = modifiers[3].post_call.call_args[0][2]
        assert isinstance(exc_res, steps.ExceptionResult)
        assert exc_res.type_ == ExceptionForTest
        modifiers[2].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod3', action, modifiers[3:], modifiers[:2],
        )
        modifiers[1].post_call.assert_not_called()
        modifiers[0].post_call.assert_not_called()

    def test_evaluate_action_fails(self, mocker):
        modifiers = [
            mocker.Mock(**{'post_call.return_value': 'mod%d' % i})
            for i in range(5)
        ]
        action = mocker.Mock(side_effect=ExceptionForTest('test'))
        obj = StepForTest('action', 'addr', 'modifiers')

        result = obj.evaluate('ctxt', modifiers[:2], modifiers[2:], action)

        assert result == 'mod2'
        modifiers[0].pre_call.assert_not_called()
        modifiers[1].pre_call.assert_not_called()
        modifiers[2].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:2], modifiers[3:], action,
        )
        modifiers[3].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:3], modifiers[4:], action,
        )
        modifiers[4].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:4], modifiers[5:], action,
        )
        action.assert_called_once_with(obj, 'ctxt')
        modifiers[4].post_call.assert_called_once_with(
            obj, 'ctxt', mocker.ANY, action, modifiers[5:], modifiers[:4],
        )
        exc_res = modifiers[4].post_call.call_args[0][2]
        assert isinstance(exc_res, steps.ExceptionResult)
        assert exc_res.type_ == ExceptionForTest
        modifiers[3].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod4', action, modifiers[4:], modifiers[:3],
        )
        modifiers[2].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod3', action, modifiers[3:], modifiers[:2],
        )
        modifiers[1].post_call.assert_not_called()
        modifiers[0].post_call.assert_not_called()

    def test_evaluate_post_call_fails(self, mocker):
        modifiers = [
            mocker.Mock(**{'post_call.return_value': 'mod%d' % i})
            for i in range(5)
        ]
        modifiers[3].post_call.side_effect = ExceptionForTest('test')
        action = mocker.Mock(return_value='action')
        obj = StepForTest('action', 'addr', 'modifiers')

        result = obj.evaluate('ctxt', modifiers[:2], modifiers[2:], action)

        assert result == 'mod2'
        modifiers[0].pre_call.assert_not_called()
        modifiers[1].pre_call.assert_not_called()
        modifiers[2].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:2], modifiers[3:], action,
        )
        modifiers[3].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:3], modifiers[4:], action,
        )
        modifiers[4].pre_call.assert_called_once_with(
            obj, 'ctxt', modifiers[:4], modifiers[5:], action,
        )
        action.assert_called_once_with(obj, 'ctxt')
        modifiers[4].post_call.assert_called_once_with(
            obj, 'ctxt', 'action', action, modifiers[5:], modifiers[:4],
        )
        modifiers[3].post_call.assert_called_once_with(
            obj, 'ctxt', 'mod4', action, modifiers[4:], modifiers[:3],
        )
        modifiers[2].post_call.assert_called_once_with(
            obj, 'ctxt', mocker.ANY, action, modifiers[3:], modifiers[:2],
        )
        exc_res = modifiers[2].post_call.call_args[0][2]
        assert isinstance(exc_res, steps.ExceptionResult)
        assert exc_res.type_ == ExceptionForTest
        modifiers[1].post_call.assert_not_called()
        modifiers[0].post_call.assert_not_called()

    def test_eager(self, mocker):
        action = mocker.Mock(eager='eager')
        obj = StepForTest(action, 'addr')

        assert obj.eager == 'eager'
