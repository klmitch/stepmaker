import six

from stepmaker import addresses


class TestStepAddress(object):
    def test_init_base(self):
        result = addresses.StepAddress('filename')

        assert result.filename == 'filename'
        assert result.path == ''

    def test_init_alt(self):
        result = addresses.StepAddress('filename', '/some/path')

        assert result.filename == 'filename'
        assert result.path == '/some/path'

    def test_str(self):
        obj = addresses.StepAddress('filename', '/some/path')

        assert six.text_type(obj) == 'filename:/some/path'

    def test_key(self):
        obj = addresses.StepAddress('filename', '/some/path')

        result = obj.key('spam')

        assert id(obj) != id(result)
        assert obj.path == '/some/path'
        assert result.filename == obj.filename
        assert result.path == '/some/path/spam'

    def test_idx(self):
        obj = addresses.StepAddress('filename', '/some/path')

        result = obj.idx(42)

        assert id(obj) != id(result)
        assert obj.path == '/some/path'
        assert result.filename == obj.filename
        assert result.path == '/some/path[42]'
