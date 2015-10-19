'''
Created on Oct 24, 2014

@author: vsam
'''
from modeling.validation import *
import sys, io, logging
import logging.handlers as lh
import pytest

def test_match():
    assert Context('foo').catches(CheckFail, CheckFail('foo'))
    assert Context('foo').catches(CheckFail, CheckFail(None))
    assert not Context('bar').catches(CheckFail, CheckFail('foo'))
    assert not Context('foo').catches(CheckFatal, CheckFatal('foo'))
    assert not Context('foo').catches(CheckFatal, CheckFatal(None))

    assert Process('foo').catches(CheckFail, CheckFail('foo'))
    assert Process('foo').catches(CheckFail, CheckFail(None))
    assert Process('foo').catches(CheckFatal, CheckFatal('foo'))
    assert Process('foo').catches(CheckFatal, CheckFatal(None))
    assert not Process('bar').catches(CheckFail, CheckFail('foo'))

def test_suppression():
    with Process('a'):
        fail('bad')

    with Process('a'):
        with Context('b'):
            fail('bad')

    with Process('a'):
        with pytest.raises(CheckException):
            with Context('b'):
                fatal('bad')

    with Process('a'):
        with pytest.raises(CheckException):
            with Context('b'):
                with Context('c'):
                    fatal('bad', scope='b')

    with Process('a'):
        with Context('b'):
            with Context('c'):
                fail('bad', scope='b')
            assert False


    with pytest.raises(IndexError):
        with Process('a'):
            with Context('b'):
                with Context('c'):
                    [1,2,3][4]  # raises IndexError
                assert False



def test_success():
    with Process('a') as p:
        fail('bad')
    assert not p.success

    with Process('a') as p:
        with Context('b'):
            fail('bad')
    assert not p.success

    with Process('a') as p:
        with pytest.raises(CheckException):
            with Context('b'):
                fatal('bad')
    assert not p.success

    with Process('a') as p:
        with pytest.raises(CheckException):
            with Context('b'):
                with Context('c'):
                    fatal('bad', scope='b')
    assert not p.success

    with Process('a') as p:
        with Context('b'):
            with Context('c'):
                fail('bad', scope='b')
            assert False
    assert not p.success


    with Process('a') as p:
        with Context('b') as b:
            with Context('c') as c:
                assert c.success
            print(c.success)
            assert c.success
        assert b.success
    assert p.success

    with Process('a') as p:
        with Context('b') as b:
            fail('bad')
        with Context('c') as c:
            inform('ok')
        assert c.success
        assert not b.success        
    assert not p.success

def test_parents():
    with Process('a') as a:
        assert a.parent is None
        assert a.process is a
        with Context('b') as b:
            with Context('c') as c:
                assert c.parent is b
                assert c.process is a
                with Process('d') as d:
                    with Context('3') as e:
                        assert e.parent is d
                        assert e.process is d
                        fail('bye')
    assert not a.success


def test_standalone_context():
    with Context():
        snafu('Hello from standalone')


@Context('func')
def ctxfunc():
    fail('error in decorated')

def test_decorator():
    been_here = False
    with Process('a') as a:
        assert a.success
        ctxfunc()
        assert not a.success
        been_here = True
    assert been_here


def test_use_logger():
    with pytest.raises(KeyError):
        fail("Hi there", ooc=KeyError)

    with pytest.raises(ValueError):
        fail("Hi there", ooc=ValueError)

    with pytest.raises(RuntimeError):
        fail("Hi there")



def test_logger():
    ss = io.StringIO()
    with Process() as tlp:
        with Process(logger=logging.getLogger('testing')) as p:
            handler = logging.StreamHandler(ss)
            fmt = logging.Formatter("Error in %(context)s: %(message)s")
            handler.setFormatter(fmt)
            p.logger.addHandler(handler)

            assert tlp.logger is not p.logger

            with Context(context="test"):
                inform('Hello world')

        inform('Not in the testing log')
    assert ss.getvalue()=='Error in test: Hello world\n'


def test_validation():
    
    with Validation() as V:
        assert V.failures==0
        V(1==1,"ok")
        assert V.failures==0
        V(1==2,"not ok")
        assert V.failures==1
        with V.section("New section"):
            V(True, "ok")
            assert V.failures==1
            with V.section("New sub section"):
                V(len(1)==1, "throws")
                assert 0, "NOT here!"
            assert V.failures==2
            V(True, "still ok")

    assert V.enter==0
    assert V.level==0
    
    with Validation(max_failures=3) as V:
        assert V.enter==1
        # Check error case
        for i in range(8):
            with V:
                assert V.enter==2
                raise Exception()
            assert V.enter==1
    
    assert V.enter==0
    assert V.failures==V.max_failures
    

def test_validation_failure_count():
    with Validation(outfile=sys.stdout) as V:

        assert V.passed()
        assert V.passed_section()
        
        V.fail(None)
        
        assert V.failures==1
        assert V.section_failures == []
        assert not V.passed()
        assert V.passed_section()
        
        with V.section(None):
            V.fail(None)
            V.fail(None)
            assert V.section_failures[-1]==2
            with V.section(None):
                V.fail(None)
                assert V.section_failures[-1]==1
            assert V.section_failures[-1]==3





