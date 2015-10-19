'''
Created on Oct 24, 2014

@author: vsam
'''
from modeling.forward import ForwardContext, ForwardReference, ForwardProxy,\
    forward_call
import pytest





def test_forward_context():
    
    fc = ForwardContext()
    
    assert fc.get_name(test_forward_context) == 'test_forward_context'
    assert fc.get_name(ForwardContext) == 'ForwardContext'
    assert fc.get_name('') == ''
    assert fc.get_name('howdy there') == 'howdy there'
    assert fc.get_name(int) == 'int'
    
    with pytest.raises(NameError):
        fc.get_name(1)
    with pytest.raises(NameError):
        fc.get_name(None)
    with pytest.raises(NameError):
        fc.get_name([])
    with pytest.raises(NameError):
        fc.get_name({})
    
    assert isinstance(fc('foo'), ForwardReference)
    
    foo = fc('foo1')
    with pytest.raises(NameError):
        fc('foo1')
    
    assert fc.TOPLEVEL['foo1'] is foo
    assert not fc.PENDING

    class Dummy:
        x=0
        def add(self, a, index=None):
            self.x = self.x+a

    d=Dummy()
    d.add(10)
    assert d.x == 10
    
    foo._.attach(d.add)
    assert foo in fc.PENDING
    
    fc.define(10, name='foo1')
    assert not fc.PENDING    
    assert d.x==20
    
    
    
def test_forward_proxy():
    
    fc = ForwardContext()

    foo = fc('foo')
    foobar = foo.bar

    FP = ForwardProxy(fc)
    
    assert FP.toplevel is fc.TOPLEVEL
    assert FP.pending is fc.PENDING
    assert FP['foo'].ref is foo
    assert FP['foo.bar'].ref is foobar
    
    with pytest.raises(KeyError):
        FP['aa']
    with pytest.raises(Exception):
        FP.parent
        
    assert foo._.name == 'foo'
    assert foobar._.name == 'bar'
    assert foo._['bar'] == foobar._
    assert foo._.parent is None
    assert foobar._.parent.ref is foo
    assert foobar._.parent == foo._
    assert foobar._ == foo._['bar'] 
    assert foobar._.context == foo._.context == FP.context == fc
    
    assert foobar._ in foo._.children
    assert foo._ == foo._
    assert foo._ != foobar._

    assert foo._.callbacks == []
    

def test_forward_call():
    
    forward = ForwardContext()
    
    class Result: 
        def foo(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
    
    R1 = Result()
    
    fa = forward_call(setattr, R1, 'x', 1)
    assert fa.barrier == 0
    assert hasattr(fa, 'result')
    assert R1.x==1

    X = forward('X')
    
    forward_call(setattr, R1, 'y', X)
    assert not hasattr(R1,'y')
    
    forward.define(10, 'X')
    assert R1.y == 10
    
    forward_call(delattr, R1, 'y')
    assert not hasattr(R1,'y')
    
    forward_call(R1.foo, 1,2, k1='a', k2='b')
    assert R1.args == (1,2)
    assert R1.kwargs == {'k1':'a', 'k2':'b'}
    

    R2 = forward('R2')
    
    def make_tuple(*x): return x
    
    tup = forward_call(make_tuple, R2.T1, R2.T2 )
    fa = forward_call(R1.foo, R2.A1, R2.A2, key1=R2.K1, key2 = tup )
    
    assert fa.barrier == 4
    
    R2 = Result()
    R2.A1 = 10
    R2.A2 = 20
    R2.K1 = 0
    R2.T1 = 'a'
    R2.T2 = 'b'
    
    forward.define(R2, 'R2')
    assert fa.barrier == 0
    
    assert R1.args == (10,20)
    assert R1.kwargs == { 'key1': 0, 'key2': ('a','b')}
    

    assert not forward.PENDING


