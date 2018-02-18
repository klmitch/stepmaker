import pytest
import six

from stepmaker import redaction


class TestRedacted(object):
    def test_init_base(self):
        result = redaction.Redacted()

        assert result.text == '<redacted>'

    def test_init_alt(self):
        result = redaction.Redacted('text')

        assert result.text == 'text'

    def test_str(self):
        obj = redaction.Redacted()

        assert six.text_type(obj) == '<redacted>'


class TestRedactedObject(object):
    def test_init_base(self):
        result = redaction.RedactedObject('obj')

        assert result.__redacted_obj__ == 'obj'
        assert result.__redacted_attrs__ == set()
        assert result.__redacted__ is redaction.redacted

    def test_init_alt(self):
        result = redaction.RedactedObject('obj', 'attrs', 'redact')

        assert result.__redacted_obj__ == 'obj'
        assert result.__redacted_attrs__ == 'attrs'
        assert result.__redacted__ == 'redact'

    def test_getattr_base(self, mocker):
        base = mocker.Mock(a=1)
        obj = redaction.RedactedObject(base, set(['b']))

        assert obj.a == 1

    def test_getattr_redacted(self, mocker):
        base = mocker.Mock(a=1)
        obj = redaction.RedactedObject(base, set(['a']))

        assert obj.a is redaction.redacted

    def test_getattr_missing(self, mocker):
        base = mocker.Mock(spec_set=[])
        obj = redaction.RedactedObject(base, set(['a']))

        with pytest.raises(AttributeError):
            obj.a

    def test_setattr_base(self, mocker):
        base = mocker.Mock(spec_set=['a'])
        obj = redaction.RedactedObject(base, set(['a']))

        obj.__redacted_something__ = 42

        assert obj.__dict__['__redacted_something__'] == 42

    def test_setattr_proxied(self, mocker):
        base = mocker.Mock(spec_set=['a'])
        obj = redaction.RedactedObject(base, set(['a']))

        obj.a = 42

        assert base.a == 42
        assert 'a' not in obj.__dict__

    def test_delattr_base(self, mocker):
        base = mocker.Mock(spec_set=['a'])
        obj = redaction.RedactedObject(base, set(['a']))
        obj.__redacted_something__ = 42

        del obj.__redacted_something__

        assert '__redacted_something__' not in obj.__dict__

    def test_delattr_proxied(self, mocker):
        base = mocker.Mock(a=42, spec_set=['a'])
        obj = redaction.RedactedObject(base, set(['a']))

        del obj.a

        assert not hasattr(base, 'a')
        assert 'a' not in obj.__dict__


class TestRedactedDict(object):
    def test_init_base(self, mocker):
        mock_init = mocker.patch.object(
            redaction.RedactedObject, '__init__',
            return_value=None,
        )

        result = redaction.RedactedDict('obj')

        assert result.__redacted_keys__ == set()
        mock_init.assert_called_once_with('obj', None, redaction.redacted)

    def test_init_alt(self, mocker):
        mock_init = mocker.patch.object(
            redaction.RedactedObject, '__init__',
            return_value=None,
        )

        result = redaction.RedactedDict('obj', 'keys', 'attrs', 'redact')

        assert result.__redacted_keys__ == 'keys'
        mock_init.assert_called_once_with('obj', 'attrs', 'redact')

    def test_len(self):
        obj = redaction.RedactedDict({'a': 1, 'b': 2})

        assert len(obj) == 2

    def test_iter(self):
        obj = redaction.RedactedDict({'a': 1, 'b': 2})

        assert set(obj) == set(['a', 'b'])

    def test_getitem_base(self):
        obj = redaction.RedactedDict({'a': 1, 'b': 2}, set(['b']))

        assert obj['a'] == 1

    def test_getitem_redacted(self):
        obj = redaction.RedactedDict({'a': 1, 'b': 2}, set(['a']))

        assert obj['a'] is redaction.redacted

    def test_getitem_missing(self):
        obj = redaction.RedactedDict({'b': 2}, set(['a']))

        with pytest.raises(KeyError):
            obj['a']

    def test_setitem(self):
        base = {'a': 1, 'b': 2}
        obj = redaction.RedactedDict(base, set(['a']))

        obj['a'] = 5

        assert base == {'a': 5, 'b': 2}

    def test_delitem(self):
        base = {'a': 1, 'b': 2}
        obj = redaction.RedactedDict(base, set(['a']))

        del obj['a']

        assert base == {'b': 2}


class TestInverter(object):
    def test_init(self):
        result = redaction.Inverter('base')

        assert result._base == 'base'

    def test_contains(self):
        base = set(['a'])
        obj = redaction.Inverter(base)

        assert 'a' not in obj
        assert 'b' in obj
