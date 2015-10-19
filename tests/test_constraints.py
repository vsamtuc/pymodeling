'''
Created on Oct 24, 2014

@author: vsam
'''

from modeling.constraints import Constraint, success, ConstraintViolation, NONNULL,\
    NULL, HAS_TYPE, BETWEEN, LENGTH, LESS_OR_EQUAL, LESS, GREATER_OR_EQUAL,\
    GREATER, Constraints, HAS_ATTR, MISSING_ATTR, is_legal_identifier
import pytest

ct = Constraint

def test_constraint():
    c = Constraint((lambda *args, **kwargs: True), "testing")
    assert success(c)
    assert success(c, 1)
    assert success(c, foo=1)
 
    c = Constraint((lambda *args, **kwargs: False), "testing")

    assert not success(c)
    assert not success(c,1)
    assert not success(c, foo=1)
    assert success(-c, 3)
    
def test_constraint_errors():
    c = ct(lambda x: x)
    with pytest.raises(ConstraintViolation):
        c(False)
    with pytest.raises(ConstraintViolation):
        c(0)
    with pytest.raises(ConstraintViolation):
        c([])
    with pytest.raises(ConstraintViolation):
        c("")
        
    with pytest.raises(TypeError):
        Constraint(1)
    with pytest.raises(TypeError):
        Constraint(lambda x:x, None)
        

def test_nonnull():
    with pytest.raises(ConstraintViolation):
        NONNULL(None)
    assert success(NONNULL, "")
    assert success(NONNULL, [])
    assert success(NONNULL, 0)
    assert success(NONNULL, False)
    assert success(NULL, None)
    assert not success(NULL, False)
    
def test_types():
    assert success(HAS_TYPE(str, int), 3)
    assert not success(HAS_TYPE(str, int), 1.0)
    
def test_between():
    assert success(BETWEEN(0,1), 0.5)
    assert not success(BETWEEN(0,1), 1.5)

def test_greater():
    assert success(GREATER(2), 3)    
    assert success(GREATER("bar"), "foo")
    assert not success(GREATER(2), 2)
    assert not success(GREATER(2), 0)
    
    assert success(-GREATER(2), 2)
    assert success(-GREATER(2), 0)

def test_greater_or_equal():
    assert success(GREATER_OR_EQUAL(2), 3)    
    assert success(GREATER_OR_EQUAL("bar"), "foo")
    assert success(GREATER_OR_EQUAL(2), 2)
    assert not success(GREATER_OR_EQUAL(2), 0)
    assert success(-GREATER_OR_EQUAL(2), 0)

def test_less():
    assert success(LESS(2), 0)    
    assert success(LESS("bar"), "abc")
    assert not success(LESS(2), 2)
    assert not success(LESS(2), 3)
    assert success(-LESS(2), 2)
    assert success(-LESS(2), 3)

def test_less_or_equal():
    assert success(LESS_OR_EQUAL(2), -3)    
    assert success(LESS_OR_EQUAL("bar"), "bar")
    assert success(LESS_OR_EQUAL(2), 2)
    assert not success(LESS_OR_EQUAL(2), 3)
    assert success(-LESS_OR_EQUAL(2), 3)


def test_length_constraint():
    a0 = ""
    a1 = "a"
    a10 = "a"*10
    a20 = "a"*20
    
    assert success(LENGTH(10), a10)
    assert success(LENGTH(10,10), a10)
    assert success(LENGTH(10,0), a10)

    assert success(LENGTH(10), a0)
    assert success(-LENGTH(10,5), a1)
    assert not success(LENGTH(10,0), a20)
    
    with pytest.raises(TypeError):
        LENGTH(0.5,0)
    with pytest.raises(ValueError):
        LENGTH()
    with pytest.raises(ValueError):
        LENGTH(3,5)
    


def test_constraints():    
    c = Constraints(NONNULL, HAS_TYPE(int))
    assert success(c, 3)
    assert not success(c, "a")
    assert not success(c, None)
    
    c = Constraints(NULL, HAS_TYPE(int), any=True)
    assert success(c, 3)
    assert not success(c, "a")
    assert success(c, None)
    
    notc = -c
    assert success(notc, "a")
    assert not success(notc, 3)
    
    
def test_empty_constraints():
    c = Constraints()
    
    assert success(c)
    assert success(c,1)
    assert success(c,0)
    assert success(c, False, 2)
    
    c = Constraints(any=True)
    assert not success(c)
    assert not success(c,1)
    assert not success(c,0)
    assert not success(c, False, 2)


def test_constraint_expr():
    c = NULL | HAS_TYPE(int)
    assert success(c, 3)
    assert success(c, None)
    assert not success(c, "aa")
    
    c = c | HAS_TYPE(str)
    assert success(c, "aa")
    
    d = GREATER(0) & LESS(10)
    assert success(d, 3)
    

def test_validation_error():
    try:
        NULL(1)
    except ConstraintViolation as verr:
        assert verr.constraint is NULL
        assert verr.args[1] == (1,)

def test_has_attr():
    class Foo:
        x=1
        y=2
        
    assert success(HAS_ATTR('x'), Foo())    
    assert success(HAS_ATTR('y'), Foo())    
    assert success(HAS_ATTR('x','y'), Foo())    
    assert success(HAS_ATTR(), Foo())    

    assert not success(HAS_ATTR('z'), Foo())
    assert not success(HAS_ATTR('x','z'), Foo())
        
def test_missing_attr():
    class Foo:
        x=1
        y=2
    assert success(MISSING_ATTR('z'), Foo())
    assert not success(MISSING_ATTR('x'), Foo())
    


@pytest.mark.parametrize("legal_id", ['a', 
                                       '_', '___', '_1',
                                       "type", "any",
                                       '____aals02_____sdkfhas______lkf____haskf_________'])
def test_legal_id(legal_id):
    assert is_legal_identifier(legal_id)

@pytest.mark.parametrize("illegal_id",[
  "1name", " name", "name ", "", "na me", "na:me", "na.me",
  "class", "if", "for", "def"
                                       ])
def test_illegal_id(illegal_id):
    assert not is_legal_identifier(illegal_id)

