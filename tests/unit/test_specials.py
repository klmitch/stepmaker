import collections
import os

from stepmaker import specials


class SpecialForTest(specials.Special):
    def __init__(self, env, var):
        super(SpecialForTest, self).__init__(env, var)

    def set(self, value):
        super(SpecialForTest, self).set(value)

    def delete(self):
        super(SpecialForTest, self).delete()


class TestSpecial(object):
    def test_init(self):
        result = SpecialForTest('env', 'var')

        assert result._env == 'env'
        assert result._var == 'var'

    def test_set(self, mocker):
        env = mocker.Mock()
        obj = SpecialForTest(env, 'var')

        obj.set('value')

        env._set.assert_called_once_with('var', 'value')

    def test_delete(self, mocker):
        env = mocker.Mock()
        obj = SpecialForTest(env, 'var')

        obj.delete()

        env._delete.assert_called_once_with('var')

    def test_raw(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'value'
        })
        obj = SpecialForTest(env, 'var')

        assert obj.raw == 'value'
        env.get_raw.assert_called_once_with('var')


class TestSpecialList(object):
    def test_with_sep(self, mocker):
        mock_init = mocker.patch.object(
            specials.SpecialList, '__init__',
            return_value=None,
        )

        result = specials.SpecialList.with_sep('|')

        assert callable(result)
        mock_init.assert_not_called()

        result2 = result('env', 'var')

        assert isinstance(result2, specials.SpecialList)
        mock_init.assert_called_once_with('env', 'var', sep='|')

    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialList, 'raw', 'val:ue',
        )

        result = specials.SpecialList('env', 'var')

        assert result._sep == os.pathsep
        assert result._value == ['val', 'ue']
        mock_init.assert_called_once_with('env', 'var')

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialList, 'raw', 'val|ue',
        )

        result = specials.SpecialList('env', 'var', '|')

        assert result._sep == '|'
        assert result._value == ['val', 'ue']
        mock_init.assert_called_once_with('env', 'var')

    def test_init_keyerror(self, mocker):
        @property
        def raw(self):
            raise KeyError('var')
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialList, 'raw', raw,
        )

        result = specials.SpecialList('env', 'var')

        assert result._sep == os.pathsep
        assert result._value == []
        mock_init.assert_called_once_with('env', 'var')

    def test_repr(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        assert repr(obj) == repr(obj._value)

    def test_len(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        assert len(obj) == 2

    def test_getitem(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        assert obj[0] == 'val'
        assert obj[1] == 'ue'

    def test_setitem(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialList, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        obj[0] = 'ue'
        obj[1] = 'val'

        assert obj._value == ['ue', 'val']
        mock_update.assert_has_calls([mocker.call(), mocker.call()])
        assert mock_update.call_count == 2

    def test_delitem(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialList, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'va:l:ue',
        })
        obj = specials.SpecialList(env, 'var')

        del obj[1]

        assert obj._value == ['va', 'ue']
        mock_update.assert_called_once_with()

    def test_update(self, mocker):
        mock_set = mocker.patch.object(
            specials.Special, 'set',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        obj._update()

        mock_set.assert_called_once_with('val:ue')

    def test_set_string(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialList, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        obj.set('ue:val')

        assert obj._value.__class__ == list
        assert obj._value == ['ue', 'val']
        mock_update.assert_called_once_with()

    def test_set_iterable(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialList, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        obj.set(('ue', 'val'))

        assert obj._value.__class__ == list
        assert obj._value == ['ue', 'val']
        mock_update.assert_called_once_with()

    def test_delete(self, mocker):
        mock_delete = mocker.patch.object(
            specials.Special, 'delete',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialList(env, 'var')

        obj.delete()

        assert obj._value == []
        mock_delete.assert_called_once_with()

    def test_insert(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialList, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'va:ue',
        })
        obj = specials.SpecialList(env, 'var')

        obj.insert(1, 'l')

        assert obj._value == ['va', 'l', 'ue']
        mock_update.assert_called_once_with()


class TestSpecialSet(object):
    def test_with_sep(self, mocker):
        mock_init = mocker.patch.object(
            specials.SpecialSet, '__init__',
            return_value=None,
        )

        result = specials.SpecialSet.with_sep('|')

        assert callable(result)
        mock_init.assert_not_called()

        result2 = result('env', 'var')

        assert isinstance(result2, specials.SpecialSet)
        mock_init.assert_called_once_with('env', 'var', sep='|')

    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialSet, 'raw', 'val:ue',
        )

        result = specials.SpecialSet('env', 'var')

        assert result._sep == os.pathsep
        assert result._value == set(['val', 'ue'])
        mock_init.assert_called_once_with('env', 'var')

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialSet, 'raw', 'val|ue',
        )

        result = specials.SpecialSet('env', 'var', '|')

        assert result._sep == '|'
        assert result._value == set(['val', 'ue'])
        mock_init.assert_called_once_with('env', 'var')

    def test_init_keyerror(self, mocker):
        @property
        def raw(self):
            raise KeyError('var')
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialSet, 'raw', raw,
        )

        result = specials.SpecialSet('env', 'var')

        assert result._sep == os.pathsep
        assert result._value == set()
        mock_init.assert_called_once_with('env', 'var')

    def test_repr(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        assert repr(obj) == repr(obj._value)

    def test_len(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        assert len(obj) == 2

    def test_iter(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        result = set(obj)

        assert result == set(['val', 'ue'])

    def test_contains(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        assert 'val' in obj
        assert 'lue' not in obj

    def test_update(self, mocker):
        mock_set = mocker.patch.object(
            specials.Special, 'set',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        obj._update()

        mock_set.assert_called_once_with('ue:val')

    def test_set_string(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialSet, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        obj.set('ue:va:l')

        assert obj._value.__class__ == set
        assert obj._value == set(['ue', 'va', 'l'])
        mock_update.assert_called_once_with()

    def test_set_iterable(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialSet, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        obj.set(('ue', 'va', 'l'))

        assert obj._value.__class__ == set
        assert obj._value == set(['ue', 'va', 'l'])
        mock_update.assert_called_once_with()

    def test_delete(self, mocker):
        mock_delete = mocker.patch.object(
            specials.Special, 'delete',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        obj.delete()

        assert obj._value == set()
        mock_delete.assert_called_once_with()

    def test_add(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialSet, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'va:ue',
        })
        obj = specials.SpecialSet(env, 'var')

        obj.add('l')

        assert obj._value == set(['va', 'ue', 'l'])
        mock_update.assert_called_once_with()

    def test_discard(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialSet, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'va:ue:l',
        })
        obj = specials.SpecialSet(env, 'var')

        obj.discard('l')

        assert obj._value == set(['va', 'ue'])
        mock_update.assert_called_once_with()


class TestSpecialDict(object):
    def test_with_sep_base(self, mocker):
        mock_init = mocker.patch.object(
            specials.SpecialDict, '__init__',
            return_value=None,
        )

        result = specials.SpecialDict.with_sep()

        assert callable(result)
        mock_init.assert_not_called()

        result2 = result('env', 'var')

        assert isinstance(result2, specials.SpecialDict)
        mock_init.assert_called_once_with(
            'env', 'var',
            item_sep=os.pathsep,
            key_sep='=',
        )

    def test_with_sep_alt(self, mocker):
        mock_init = mocker.patch.object(
            specials.SpecialDict, '__init__',
            return_value=None,
        )

        result = specials.SpecialDict.with_sep('|', '/')

        assert callable(result)
        mock_init.assert_not_called()

        result2 = result('env', 'var')

        assert isinstance(result2, specials.SpecialDict)
        mock_init.assert_called_once_with(
            'env', 'var',
            item_sep='|',
            key_sep='/',
        )

    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialDict, 'raw', 'k1=v1:k2=v2',
        )

        result = specials.SpecialDict('env', 'var')

        assert result._item_sep == os.pathsep
        assert result._key_sep == '='
        assert result._value == {'k1': 'v1', 'k2': 'v2'}
        mock_init.assert_called_once_with('env', 'var')

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialDict, 'raw', 'k1/v1|k2/v2',
        )

        result = specials.SpecialDict('env', 'var', '|', '/')

        assert result._item_sep == '|'
        assert result._key_sep == '/'
        assert result._value == {'k1': 'v1', 'k2': 'v2'}
        mock_init.assert_called_once_with('env', 'var')

    def test_init_keyerror(self, mocker):
        @property
        def raw(self):
            raise KeyError('var')
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialDict, 'raw', raw,
        )

        result = specials.SpecialDict('env', 'var')

        assert result._item_sep == os.pathsep
        assert result._key_sep == '='
        assert result._value == {}
        mock_init.assert_called_once_with('env', 'var')

    def test_repr(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        assert repr(obj) == repr(obj._value)

    def test_len(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        assert len(obj) == 2

    def test_iter(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        result = set(obj)

        assert result == set(['k1', 'k2'])

    def test_getitem(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        assert obj['k1'] == 'v1'
        assert obj['k2'] == 'v2'

    def test_setitem(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        obj['k2'] = 'v3'
        obj['k3'] = 'v4'

        assert obj._value == {'k1': 'v1', 'k2': 'v3', 'k3': 'v4'}
        mock_update.assert_has_calls([mocker.call(), mocker.call()])
        assert mock_update.call_count == 2

    def test_delitem(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2:k3=v3',
        })
        obj = specials.SpecialDict(env, 'var')

        del obj['k2']

        assert obj._value == {'k1': 'v1', 'k3': 'v3'}
        mock_update.assert_called_once_with()

    def test_update(self, mocker):
        mock_set = mocker.patch.object(
            specials.Special, 'set',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2:k3=v3',
        })
        obj = specials.SpecialDict(env, 'var')

        obj._update()

        mock_set.assert_called_once_with('k1=v1:k2:k3=v3')

    def test_split(self, mocker):
        @property
        def raw(self):
            raise KeyError('var')
        mocker.patch.object(
            specials.SpecialDict, 'raw', raw,
        )
        obj = specials.SpecialDict('env', 'var')

        result = obj._split('k1=v1:k2:k3=v3')

        assert result == {'k1': 'v1', 'k2': None, 'k3': 'v3'}

    def test_set_string(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        obj.set('k3=v3:k4=v4')

        assert obj._value.__class__ == dict
        assert obj._value == {'k3': 'v3', 'k4': 'v4'}
        mock_update.assert_called_once_with()

    def test_set_iterable(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialDict(env, 'var')

        obj.set([('k3', 'v3'), ('k4', 'v4')])

        assert obj._value.__class__ == dict
        assert obj._value == {'k3': 'v3', 'k4': 'v4'}
        mock_update.assert_called_once_with()

    def test_delete(self, mocker):
        mock_delete = mocker.patch.object(
            specials.Special, 'delete',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialDict(env, 'var')

        obj.delete()

        assert obj._value == {}
        mock_delete.assert_called_once_with()


class TestSpecialOrderedDict(object):
    def test_with_sep_base(self, mocker):
        mock_init = mocker.patch.object(
            specials.SpecialOrderedDict, '__init__',
            return_value=None,
        )

        result = specials.SpecialOrderedDict.with_sep()

        assert callable(result)
        mock_init.assert_not_called()

        result2 = result('env', 'var')

        assert isinstance(result2, specials.SpecialOrderedDict)
        mock_init.assert_called_once_with(
            'env', 'var',
            item_sep=os.pathsep,
            key_sep='=',
        )

    def test_with_sep_alt(self, mocker):
        mock_init = mocker.patch.object(
            specials.SpecialOrderedDict, '__init__',
            return_value=None,
        )

        result = specials.SpecialOrderedDict.with_sep('|', '/')

        assert callable(result)
        mock_init.assert_not_called()

        result2 = result('env', 'var')

        assert isinstance(result2, specials.SpecialOrderedDict)
        mock_init.assert_called_once_with(
            'env', 'var',
            item_sep='|',
            key_sep='/',
        )

    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialOrderedDict, 'raw', 'k1=v1:k2=v2',
        )

        result = specials.SpecialOrderedDict('env', 'var')

        assert result._item_sep == os.pathsep
        assert result._key_sep == '='
        assert result._value == {'k1': 'v1', 'k2': 'v2'}
        mock_init.assert_called_once_with('env', 'var')

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialOrderedDict, 'raw', 'k1/v1|k2/v2',
        )

        result = specials.SpecialOrderedDict('env', 'var', '|', '/')

        assert result._item_sep == '|'
        assert result._key_sep == '/'
        assert result._value == {'k1': 'v1', 'k2': 'v2'}
        mock_init.assert_called_once_with('env', 'var')

    def test_init_keyerror(self, mocker):
        @property
        def raw(self):
            raise KeyError('var')
        mock_init = mocker.patch.object(
            specials.Special, '__init__',
            return_value=None,
        )
        mocker.patch.object(
            specials.SpecialOrderedDict, 'raw', raw,
        )

        result = specials.SpecialOrderedDict('env', 'var')

        assert result._item_sep == os.pathsep
        assert result._key_sep == '='
        assert result._value.__class__ == collections.OrderedDict
        assert result._value == {}
        mock_init.assert_called_once_with('env', 'var')

    def test_repr(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        assert repr(obj) == repr(obj._value)

    def test_len(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        assert len(obj) == 2

    def test_iter(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        result = set(obj)

        assert result == set(['k1', 'k2'])

    def test_getitem(self, mocker):
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        assert obj['k1'] == 'v1'
        assert obj['k2'] == 'v2'

    def test_setitem(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialOrderedDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        obj['k2'] = 'v3'
        obj['k3'] = 'v4'

        assert obj._value == {'k1': 'v1', 'k2': 'v3', 'k3': 'v4'}
        mock_update.assert_has_calls([mocker.call(), mocker.call()])
        assert mock_update.call_count == 2

    def test_delitem(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialOrderedDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2:k3=v3',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        del obj['k2']

        assert obj._value == {'k1': 'v1', 'k3': 'v3'}
        mock_update.assert_called_once_with()

    def test_update(self, mocker):
        mock_set = mocker.patch.object(
            specials.Special, 'set',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k3=v3:k2:k1=v1',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        obj._update()

        mock_set.assert_called_once_with('k3=v3:k2:k1=v1')

    def test_split(self, mocker):
        @property
        def raw(self):
            raise KeyError('var')
        mocker.patch.object(
            specials.SpecialOrderedDict, 'raw', raw,
        )
        obj = specials.SpecialOrderedDict('env', 'var')

        result = obj._split('k1=v1:k2:k3=v3')

        assert result.__class__ == collections.OrderedDict
        assert result == {'k1': 'v1', 'k2': None, 'k3': 'v3'}

    def test_set_string(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialOrderedDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        obj.set('k3=v3:k4=v4')

        assert obj._value.__class__ == collections.OrderedDict
        assert obj._value == {'k3': 'v3', 'k4': 'v4'}
        mock_update.assert_called_once_with()

    def test_set_ordereddict(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialOrderedDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')
        value = collections.OrderedDict([('k4', 'v4'), ('k3', 'v3')])

        obj.set(value)

        assert obj._value.__class__ == collections.OrderedDict
        assert obj._value == {'k3': 'v3', 'k4': 'v4'}
        assert id(obj._value) != id(value)
        mock_update.assert_called_once_with()

    def test_set_iterable(self, mocker):
        mock_update = mocker.patch.object(
            specials.SpecialOrderedDict, '_update',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'k1=v1:k2=v2',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        obj.set([('k3', 'v3'), ('k4', 'v4')])

        assert obj._value.__class__ == collections.OrderedDict
        assert obj._value == {'k3': 'v3', 'k4': 'v4'}
        mock_update.assert_called_once_with()

    def test_delete(self, mocker):
        mock_delete = mocker.patch.object(
            specials.Special, 'delete',
        )
        env = mocker.Mock(**{
            'get_raw.return_value': 'val:ue',
        })
        obj = specials.SpecialOrderedDict(env, 'var')

        obj.delete()

        assert obj._value.__class__ == collections.OrderedDict
        assert obj._value == {}
        mock_delete.assert_called_once_with()
