import signal

import six

from stepmaker import environment
from stepmaker import exceptions


class TestStepError(object):
    def test_init_base(self):
        result = exceptions.StepError('some message')

        assert six.text_type(result) == 'some message'
        assert result.addr is None

    def test_init_alt(self):
        result = exceptions.StepError('some message', 'addr')

        assert six.text_type(result) == 'some message (addr)'
        assert result.addr == 'addr'


class TestAbortStep(object):
    def test_init_base(self):
        result = exceptions.AbortStep()

        assert result.result is exceptions.skipped

    def test_init_alt(self):
        result = exceptions.AbortStep('result')

        assert result.result == 'result'


class TestProcessError(object):
    def test_init_signal(self):
        res = environment.CompletedProcess(['cmd', 'a1', 'a2'], -signal.SIGINT)

        result = exceptions.ProcessError(res)

        assert six.text_type(result) == 'Command "cmd" died with SIGINT'
        assert result.result == res

    def test_init_unknown_signal(self):
        res = environment.CompletedProcess(['cmd', 'a1', 'a2'], -1000)

        result = exceptions.ProcessError(res)

        assert (six.text_type(result) ==
                'Command "cmd" died with unknown signal 1000')
        assert result.result == res

    def test_init_nonzero_return(self):
        res = environment.CompletedProcess(['cmd', 'a1', 'a2'], 42)

        result = exceptions.ProcessError(res)

        assert (six.text_type(result) ==
                'Command "cmd" returned non-zero exit status 42')
        assert result.result == res

    def test_init_zero_return(self):
        res = environment.CompletedProcess(['cmd', 'a1', 'a2'], 0)

        result = exceptions.ProcessError(res)

        assert six.text_type(result) == 'Command "cmd" successful'
        assert result.result == res
