import os

import pytest
from six.moves import builtins

from stepmaker import environment
from stepmaker import exceptions


class ExceptionForTest(Exception):
    pass


class TestCompletedProcess(object):
    def test_init_base(self):
        result = environment.CompletedProcess(['a1', 'a2', 'a3'], 42)

        assert result.args == ['a1', 'a2', 'a3']
        assert result.returncode == 42
        assert result.stdout is None
        assert result.stderr is None

    def test_init_alt(self):
        result = environment.CompletedProcess(
            ['a1', 'a2', 'a3'], 42, 'stdout', 'stderr'
        )

        assert result.args == ['a1', 'a2', 'a3']
        assert result.returncode == 42
        assert result.stdout == 'stdout'
        assert result.stderr == 'stderr'


class TestEnvironment(object):
    def test_init_base(self, mocker):
        mocker.patch.object(
            environment.os, 'getcwd',
            return_value='/some/path',
        )
        mock_canonicalize_path = mocker.patch.object(
            environment.utils, '_canonicalize_path',
            return_value='/real/path',
        )

        result = environment.Environment()

        assert result._environ == os.environ
        assert id(result._environ) != id(os.environ)
        assert result._cwd == '/real/path'
        assert result._specials == {}
        assert result._special_cache == {}
        mock_canonicalize_path.assert_called_once_with(
            '/some/path', os.curdir,
        )

    def test_init_alt(self, mocker):
        mocker.patch.object(
            environment.os, 'getcwd',
            return_value='/some/path',
        )
        mock_canonicalize_path = mocker.patch.object(
            environment.utils, '_canonicalize_path',
            return_value='/real/path',
        )

        result = environment.Environment({'a': 1, 'b': 2}, '/c/w/d', c=3, d=4)

        assert result._environ == {'a': 1, 'b': 2}
        assert id(result._environ) != id(os.environ)
        assert result._cwd == '/real/path'
        assert result._specials == {'c': 3, 'd': 4}
        assert result._special_cache == {}
        mock_canonicalize_path.assert_called_once_with(
            '/some/path', '/c/w/d',
        )

    def test_len(self):
        obj = environment.Environment({'a': 1, 'b': 2})

        assert len(obj) == 2

    def test_iter(self):
        obj = environment.Environment({'a': 1, 'b': 2})

        result = set(obj)

        assert result == set(['a', 'b'])

    def test_getitem_missing_key(self, mocker):
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value='special',
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        with pytest.raises(KeyError):
            obj['c']
        mock_get_special.assert_not_called()

    def test_getitem_with_key(self, mocker):
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value='special',
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        assert obj['a'] == 1
        mock_get_special.assert_not_called()

    def test_getitem_with_special(self, mocker):
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value='special',
        )
        obj = environment.Environment({'a': 1, 'b': 2}, a='spam')

        assert obj['a'] == 'special'
        mock_get_special.assert_called_once_with('a')

    def test_setitem_base(self, mocker):
        special = mocker.Mock()
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value=special,
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        obj['a'] = 5

        assert obj._environ == {'a': 5, 'b': 2}
        mock_get_special.assert_not_called()
        special.set.assert_not_called()

    def test_setitem_with_special(self, mocker):
        special = mocker.Mock()
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value=special,
        )
        obj = environment.Environment({'a': 1, 'b': 2}, a='special')

        obj['a'] = 5

        assert obj._environ == {'a': 1, 'b': 2}
        mock_get_special.assert_called_once_with('a')
        special.set.assert_called_once_with(5)

    def test_delitem_base(self, mocker):
        special = mocker.Mock()
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value=special,
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        del obj['a']

        assert obj._environ == {'b': 2}
        mock_get_special.assert_not_called()
        special.delete.assert_not_called()

    def test_delitem_missing_key(self, mocker):
        special = mocker.Mock()
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value=special,
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        with pytest.raises(KeyError):
            del obj['c']
        assert obj._environ == {'a': 1, 'b': 2}
        mock_get_special.assert_not_called()
        special.delete.assert_not_called()

    def test_delitem_with_special(self, mocker):
        special = mocker.Mock()
        mock_get_special = mocker.patch.object(
            environment.Environment, '_get_special',
            return_value=special,
        )
        obj = environment.Environment({'a': 1, 'b': 2}, a='special')

        del obj['a']

        assert obj._environ == {'a': 1, 'b': 2}
        mock_get_special.assert_called_once_with('a')
        special.delete.assert_called_once_with()

    def test_call_base(self, mocker):
        process = mocker.Mock(**{
            'communicate.return_value': ('stdout', 'stderr'),
            'poll.return_value': 0,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        result = obj(['cmd', 'a1', 'a2'], a=1, b=2)

        assert isinstance(result, environment.CompletedProcess)
        assert result.args == ['cmd', 'a1', 'a2']
        assert result.returncode == 0
        assert result.stdout == 'stdout'
        assert result.stderr == 'stderr'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )
        process.assert_has_calls([
            mocker.call.communicate(None),
            mocker.call.poll(),
        ])
        assert len(process.method_calls) == 2

    def test_call_args_str(self, mocker):
        process = mocker.Mock(**{
            'communicate.return_value': ('stdout', 'stderr'),
            'poll.return_value': 0,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        result = obj('cmd a1 a2', a=1, b=2)

        assert isinstance(result, environment.CompletedProcess)
        assert result.args == ['cmd', 'a1', 'a2']
        assert result.returncode == 0
        assert result.stdout == 'stdout'
        assert result.stderr == 'stderr'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )
        process.assert_has_calls([
            mocker.call.communicate(None),
            mocker.call.poll(),
        ])
        assert len(process.method_calls) == 2

    def test_call_with_input(self, mocker):
        process = mocker.Mock(**{
            'communicate.return_value': ('stdout', 'stderr'),
            'poll.return_value': 0,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        result = obj(['cmd', 'a1', 'a2'], a=1, b=2, input='text')

        assert isinstance(result, environment.CompletedProcess)
        assert result.args == ['cmd', 'a1', 'a2']
        assert result.returncode == 0
        assert result.stdout == 'stdout'
        assert result.stderr == 'stderr'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2, 'stdin': environment.PIPE},
        )
        process.assert_has_calls([
            mocker.call.communicate('text'),
            mocker.call.poll(),
        ])
        assert len(process.method_calls) == 2

    def test_call_both_input_and_stdin(self, mocker):
        process = mocker.Mock(**{
            'communicate.return_value': ('stdout', 'stderr'),
            'poll.return_value': 0,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        with pytest.raises(ValueError):
            obj(['cmd', 'a1', 'a2'], a=1, b=2, input='text', stdin='pipe')
        mock_system.assert_not_called()
        assert len(process.method_calls) == 0

    def test_call_communicate_fail(self, mocker):
        process = mocker.Mock(**{
            'communicate.side_effect': ExceptionForTest('test'),
            'poll.return_value': 0,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        with pytest.raises(ExceptionForTest):
            obj(['cmd', 'a1', 'a2'], a=1, b=2)
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )
        process.assert_has_calls([
            mocker.call.communicate(None),
            mocker.call.kill(),
            mocker.call.wait(),
        ])
        assert len(process.method_calls) == 3

    def test_call_nonzero_returncode(self, mocker):
        process = mocker.Mock(**{
            'communicate.return_value': ('stdout', 'stderr'),
            'poll.return_value': 5,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        result = obj(['cmd', 'a1', 'a2'], a=1, b=2)

        assert isinstance(result, environment.CompletedProcess)
        assert result.args == ['cmd', 'a1', 'a2']
        assert result.returncode == 5
        assert result.stdout == 'stdout'
        assert result.stderr == 'stderr'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )
        process.assert_has_calls([
            mocker.call.communicate(None),
            mocker.call.poll(),
        ])
        assert len(process.method_calls) == 2

    def test_call_nonzero_returncode_check(self, mocker):
        process = mocker.Mock(**{
            'communicate.return_value': ('stdout', 'stderr'),
            'poll.return_value': 5,
        })
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value=process,
        )
        obj = environment.Environment()

        with pytest.raises(exceptions.ProcessError) as exc_info:
            obj(['cmd', 'a1', 'a2'], a=1, b=2, check=True)
        assert isinstance(exc_info.value.result, environment.CompletedProcess)
        assert exc_info.value.result.args == ['cmd', 'a1', 'a2']
        assert exc_info.value.result.returncode == 5
        assert exc_info.value.result.stdout == 'stdout'
        assert exc_info.value.result.stderr == 'stderr'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )
        process.assert_has_calls([
            mocker.call.communicate(None),
            mocker.call.poll(),
        ])
        assert len(process.method_calls) == 2

    def test_get_special_cached(self, mocker):
        special_factory = mocker.Mock(
            return_value='special',
        )
        obj = environment.Environment({'a': 1, 'b': 2}, a=special_factory)
        obj._special_cache['a'] = 'cached'

        result = obj._get_special('a')

        assert result == 'cached'
        assert obj._special_cache == {'a': 'cached'}
        special_factory.assert_not_called()

    def test_get_special_uncached(self, mocker):
        special_factory = mocker.Mock(
            return_value='special',
        )
        obj = environment.Environment({'a': 1, 'b': 2}, a=special_factory)

        result = obj._get_special('a')

        assert result == 'special'
        assert obj._special_cache == {'a': 'special'}
        special_factory.assert_called_once_with(obj, 'a')

    def test_set(self):
        obj = environment.Environment({'a': 1, 'b': 2})

        obj._set('a', 5)

        assert obj._environ == {'a': 5, 'b': 2}

    def test_delete_exists(self):
        obj = environment.Environment({'a': 1, 'b': 2})

        obj._delete('a')

        assert obj._environ == {'b': 2}

    def test_delete_missing(self):
        obj = environment.Environment({'a': 1, 'b': 2})

        obj._delete('c')

        assert obj._environ == {'a': 1, 'b': 2}

    def test_system_base(self, mocker):
        mock_filename = mocker.patch.object(
            environment.Environment, 'filename',
            return_value='/some/path',
        )
        mock_Popen = mocker.patch.object(
            environment.subprocess, 'Popen',
            return_value='result',
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        result = obj._system('args', {'c': 3, 'd': 4})

        assert result == 'result'
        mock_filename.assert_not_called()
        mock_Popen.assert_called_once_with(
            'args',
            c=3,
            d=4,
            cwd=obj._cwd,
            env={'a': 1, 'b': 2},
            close_fds=True,
        )

    def test_system_alt(self, mocker):
        mock_filename = mocker.patch.object(
            environment.Environment, 'filename',
            return_value='/some/path',
        )
        mock_Popen = mocker.patch.object(
            environment.subprocess, 'Popen',
            return_value='result',
        )
        obj = environment.Environment({'a': 1, 'b': 2})

        result = obj._system('args', {
            'c': 3,
            'd': 4,
            'cwd': '/other/path',
            'env': {'a': 2, 'b': 1},
            'close_fds': False
        })

        assert result == 'result'
        mock_filename.assert_called_once_with('/other/path')
        mock_Popen.assert_called_once_with(
            'args',
            c=3,
            d=4,
            cwd='/some/path',
            env={'a': 2, 'b': 1},
            close_fds=False,
        )

    def test_setdefault_missing(self, mocker):
        obj = environment.Environment({'a': 1, 'b': 2})

        result = obj.setdefault('c', 3)

        assert result == 3
        assert obj._environ == {'a': 1, 'b': 2, 'c': 3}

    def test_setdefault_present(self, mocker):
        obj = environment.Environment({'a': 1, 'b': 2})

        result = obj.setdefault('a', 3)

        assert result == 1
        assert obj._environ == {'a': 1, 'b': 2}

    def test_copy(self):
        obj = environment.Environment({'a': 1, 'b': 2}, '/c/w/d', c=3, d=4)

        result = obj.copy()

        assert id(result) != id(obj)
        assert result._environ == obj._environ
        assert id(result._environ) != id(obj._environ)
        assert result._cwd == '/c/w/d'
        assert result._specials == {'c': 3, 'd': 4}
        assert result._special_cache == {}

    def test_register_base(self):
        obj = environment.Environment({'a': 1, 'b': 2}, c=3, d=4)
        obj._special_cache['c'] = 'cached'

        result = obj.register('c', 3)

        assert result == 3
        assert obj._specials == {'c': 3, 'd': 4}
        assert obj._special_cache == {'c': 'cached'}

    def test_register_change(self):
        obj = environment.Environment({'a': 1, 'b': 2}, c=3, d=4)
        obj._special_cache['c'] = 'cached'

        result = obj.register('c', 5)

        assert result == 3
        assert obj._specials == {'c': 5, 'd': 4}
        assert obj._special_cache == {}

    def test_register_unregister(self):
        obj = environment.Environment({'a': 1, 'b': 2}, c=3, d=4)
        obj._special_cache['c'] = 'cached'

        result = obj.register('c')

        assert result == 3
        assert obj._specials == {'d': 4}
        assert obj._special_cache == {}

    def test_get_raw_missing_key_no_default(self, mocker):
        obj = environment.Environment({'a': 1, 'b': 2}, c='special')

        with pytest.raises(KeyError):
            obj.get_raw('c')

    def test_get_raw_missing_key_with_default(self, mocker):
        obj = environment.Environment({'a': 1, 'b': 2}, c='special')

        result = obj.get_raw('c', 'default')

        assert result == 'default'

    def test_get_raw_with_key(self, mocker):
        obj = environment.Environment({'a': 1, 'b': 2}, a='special')

        result = obj.get_raw('a', 'default')

        assert result == 1

    def test_filename(self, mocker):
        obj = environment.Environment()
        # Note: must be set up after initializing the environment
        mock_canonicalize_path = mocker.patch.object(
            environment.utils, '_canonicalize_path',
            return_value='/canon/path',
        )

        result = obj.filename('file.name')

        assert result == '/canon/path'
        mock_canonicalize_path.assert_called_once_with(obj._cwd, 'file.name')

    def test_open_base(self, mocker):
        mock_open = mocker.patch.object(
            builtins, 'open',
            return_value='handle',
        )
        mock_filename = mocker.patch.object(
            environment.Environment, 'filename',
            return_value='/some/file',
        )
        obj = environment.Environment()

        result = obj.open('file.name')

        assert result == 'handle'
        mock_filename.assert_called_once_with('file.name')
        mock_open.assert_called_once_with('/some/file', 'r', -1)

    def test_open_alt(self, mocker):
        mock_open = mocker.patch.object(
            builtins, 'open',
            return_value='handle',
        )
        mock_filename = mocker.patch.object(
            environment.Environment, 'filename',
            return_value='/some/file',
        )
        obj = environment.Environment()

        result = obj.open('file.name', 'w', 1)

        assert result == 'handle'
        mock_filename.assert_called_once_with('file.name')
        mock_open.assert_called_once_with('/some/file', 'w', 1)

    def test_popen_base(self, mocker):
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value='result',
        )
        obj = environment.Environment()

        result = obj.popen(['cmd', 'a1', 'a2'], a=1, b=2)

        assert result == 'result'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )

    def test_popen_arg_str(self, mocker):
        mock_system = mocker.patch.object(
            environment.Environment, '_system',
            return_value='result',
        )
        obj = environment.Environment()

        result = obj.popen('cmd a1 a2', a=1, b=2)

        assert result == 'result'
        mock_system.assert_called_once_with(
            ['cmd', 'a1', 'a2'], {'a': 1, 'b': 2},
        )

    def test_cwd_get(self):
        obj = environment.Environment()

        assert obj.cwd == obj._cwd

    def test_cwd_set(self, mocker):
        mock_filename = mocker.patch.object(
            environment.Environment, 'filename',
            return_value='/new/cwd',
        )
        obj = environment.Environment()

        obj.cwd = '/some/path'

        assert obj._cwd == '/new/cwd'
        mock_filename.assert_called_once_with('/some/path')
