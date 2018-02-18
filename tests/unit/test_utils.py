import pytest

from stepmaker import addresses
from stepmaker import exceptions
from stepmaker import utils


class ExceptionForTest(Exception):
    pass


class ValidationException(Exception):
    def __init__(self, message, path):
        super(ValidationException, self).__init__(message)
        self.path = path


class TestCanonicalizePath(object):
    def test_absolute(self, mocker):
        mocker.patch.object(
            utils.os.path, 'isabs',
            return_value=True,
        )
        mock_join = mocker.patch.object(
            utils.os.path, 'join',
            return_value='/joined/path',
        )
        mock_abspath = mocker.patch.object(
            utils.os.path, 'abspath',
            return_value='/absolute/path',
        )

        result = utils._canonicalize_path('/some/path', '/other/path')

        assert result == '/absolute/path'
        mock_join.assert_not_called()
        mock_abspath.assert_called_once_with('/other/path')

    def test_relative(self, mocker):
        mocker.patch.object(
            utils.os.path, 'isabs',
            return_value=False,
        )
        mock_join = mocker.patch.object(
            utils.os.path, 'join',
            return_value='/joined/path',
        )
        mock_abspath = mocker.patch.object(
            utils.os.path, 'abspath',
            return_value='/absolute/path',
        )

        result = utils._canonicalize_path('/some/path', 'other/path')

        assert result == '/absolute/path'
        mock_join.assert_called_once_with('/some/path', 'other/path')
        mock_abspath.assert_called_once_with('/joined/path')


class TestInheritSet(object):
    def test_base(self, mocker):
        bases = (
            mocker.Mock(a=set(['a', 'b']), spec=['a']),
            mocker.Mock(a=set(['c']), b=set(['d']), spec=['a', 'b']),
            mocker.Mock(b=set(['e']), c=set(['f']), spec=['b', 'c']),
        )
        namespace = {
            'a': set(['g']),
            'd': set(['h']),
        }

        utils._inherit_set(['a', 'b', 'c', 'd', 'e'], bases, namespace)

        assert namespace == {
            'a': set(['a', 'b', 'c', 'g']),
            'b': set(['d', 'e']),
            'c': set(['f']),
            'd': set(['h']),
            'e': set(),
        }


class TestSortVisit(object):
    def test_base(self):
        adjacency = {
            'b': {'before': ['d'], 'mod': '<b>'},
            'c': {'before': [], 'mod': '<c>'},
            'd': {'before': ['b'], 'mod': '<d>'},
            'e': {'before': ['f'], 'mod': '<e>'},
        }
        node = {'before': ['c', 'd', 'f'], 'mod': '<a>'}
        result = []

        utils._sort_visit(adjacency, result, node)

        assert adjacency == {
            'e': {'before': ['f'], 'mod': '<e>'},
        }
        assert result == ['<b>', '<d>', '<c>', '<a>']


class TestSortModifiers(object):
    def test_base(self, mocker):
        def fake_sort_visit(adjacency, result, node):
            result[:] = ['a', 'b', 'c']
            adjacency.pop('c', None)
        mock_sort_visit = mocker.patch.object(
            utils, '_sort_visit',
            side_effect=fake_sort_visit,
        )
        modifiers = {
            'a': mocker.Mock(before=set(['c', 'f']), after=set()),
            'b': mocker.Mock(before=set(['d']), after=set()),
            'c': mocker.Mock(before=set(), after=set(['f'])),
            'd': mocker.Mock(before=set(['b']), after=set(['a'])),
            'e': mocker.Mock(before=set(['f']), after=set()),
        }
        adjacency = {
            'a': {'before': set(['c', 'd']), 'mod': modifiers['a']},
            'b': {'before': set(['d']), 'mod': modifiers['b']},
            'd': {'before': set(['b']), 'mod': modifiers['d']},
            'e': {'before': set(), 'mod': modifiers['e']},
        }

        result = utils._sort_modifiers(modifiers)

        assert result == ['c', 'b', 'a']
        mock_sort_visit.assert_has_calls([
            mocker.call({}, result, adjacency[key])
            for key in sorted(adjacency, reverse=True)
        ])
        assert mock_sort_visit.call_count == len(adjacency)


class TestJsonschemaValidator(object):
    def test_base(self):
        addr = addresses.StepAddress('file.name', 'path')

        with utils.jsonschema_validator(addr):
            result = 42

        assert result == 42

    def test_base_exception(self):
        addr = addresses.StepAddress('file.name', 'path')

        with pytest.raises(ExceptionForTest):
            with utils.jsonschema_validator(addr):
                raise ExceptionForTest('test')

    def test_validation_error(self):
        addr = addresses.StepAddress('file.name', 'path')

        with pytest.raises(exceptions.StepError) as exc_info:
            with utils.jsonschema_validator(addr):
                raise ValidationException('some message', ['a', 1, 'b', 2])

        assert isinstance(exc_info.value.addr, addresses.StepAddress)
        assert exc_info.value.addr.filename == 'file.name'
        assert exc_info.value.addr.path == 'path/a[1]/b[2]'
