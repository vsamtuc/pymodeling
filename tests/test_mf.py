'''
Test module for mf

Created on Sep 28, 2014

@author: vsam
'''


import pytest
from modeling.mf import *
from modeling.constraints import *
from modeling.instrument import attr_descriptor

import sys
from modeling.forward import ForwardContext, ForwardProxy


class clist:
    def __init__(self, name, *sc):
        self.name = name
        self.sc = c3_merge([[self]]+
            [list(c.sc) for c in sc] + [list(sc)])
    def __repr__(self):
        return self.name

def test_c3_merge():
    x1 = clist('x1')
    x2 = clist('x2')

    assert x1.sc == [x1]
    assert x2.sc == [x2]

    y1 = clist('y1', x1)
    y2 = clist('y2', x1)
    y3 = clist('y3', x2)

    assert y1.sc == [y1,x1]
    assert y2.sc == [y2,x1]
    assert y3.sc == [y3,x2]

    z1 = clist('z1', y1,y3,y2)
    assert z1.sc == [z1, y1, y3, x2, y2, x1]

    z2 = clist('z2', z1, x1)
    assert z2.sc == [z2, z1, y1, y3, x2, y2, x1]

    z3 = clist('z3', y1, y2, y3)
    assert z3.sc == [z3, y1, y2, x1, y3, x2]

    with pytest.raises(ValueError):
        clist('z3', x1, z1)
    with pytest.raises(ValueError):
        clist('z4', z1, z3)
    with pytest.raises(ValueError):
        clist('z5', z3, z1)


def test_attribute():
    Attribute()
    
    assert Attribute(name='foo').name=="foo"
    assert Attribute("foo").name=="foo"
    
    assert Attribute("foo",None,int,1).default==1    
    assert Attribute("foo",None,int).default== Ellipsis
    
    assert Attribute(type=int).type is int
    assert Attribute().type is object    
    
    
def test_attribute_errors():
    with pytest.raises(TypeError):
        Attribute(type=1)
    with pytest.raises(TypeError):
        Attribute(type=None)
    with pytest.raises(TypeError):
        Attribute(type=int, default=None, nullable=0)
    with pytest.raises(TypeError):
        Attribute(type=int, default="2")
        
    
def test_relationship():
    A = Class('A')
    B = Class('B')
    
    relationships(A, 'a', RelKind.ONE, B, 'b', RelKind.ORDERED)
    
    rA = list(A.relationships)[0]
    rB = list(B.relationships)[0]
    
    assert rA.target is B
    assert rA.name == 'a'
    assert rA.kind == RelKind.ONE
    
    assert rB.target is A
    assert rB.name == 'b'
    assert rB.kind == RelKind.ORDERED
    

#
# declare a good complex schema
#


def test_class_arguments():
    try:
        Class('x',None)
        Class('x', [Class('y',None)])
        Class('x', None, [Attribute()])
        Class('x', None, [])        
    except:
        assert False
    
def test_class_arguemnt_errors():
    with pytest.raises(ValueError):
        Class('', int)
    with pytest.raises(TypeError):
        Class('foo', int, [1,2])
    with pytest.raises(TypeError):
        Class('foo', int, [])
    

    
def test_class_hierarchy():
    Person = Class('Person', None, [Attribute('name', type=str)])
    Employee = Class('Employee', [Person], [
                                          Attribute('salary', type=float, default=1000.0),
                                          Attribute('position', type=str, nullable=True)
                                          ])
    Manager = Class('Manager', [Employee])
    Department = Class('Department',None, [
                                           Attribute('name', type=str)
                                           ])
    relationships(Employee,'department',RelKind.ONE, Department, 'employees', RelKind.MANY)
    relationships(Manager, 'manages', RelKind.ONE, Department, 'manager', RelKind.ONE)

    
    assert Manager.is_subclass(Person)
    assert Person in Manager.all_proper_superclasses()
    assert Manager.is_subclass(Manager)
    
    assert not Person.is_subclass(Employee)
    
    with pytest.raises(TypeError):
        Manager.is_subclass('Employee')
    
    Owner = Class('Owner', [Person], [
            Attribute('stake',type=float)
    ])

    OwnerManager = Class('OwnerManager', [Owner, Manager])

    assert Owner.is_subclass(Person)
    assert OwnerManager.is_subclass(Person)
    assert OwnerManager.is_subclass(Owner)
    assert OwnerManager.is_subclass(Manager)
    assert OwnerManager.is_subclass(OwnerManager)

    assert OwnerManager.get_attribute('stake') is Owner.get_attribute('stake')
    assert OwnerManager.get_attribute('name') is Owner.get_attribute('name')
    assert OwnerManager.get_attribute('name') is Person.get_attribute('name')
    assert OwnerManager.get_attribute('name') is Manager.get_attribute('name')


def test_annotation_syntax():
    
    Ann = annotation_class('Ann', [])
    Ann2 = annotation_class('Ann2', ['a','b'])
    
    @Ann()
    def foo(): pass
    assert list(annotations_of(foo)) == [Ann()]
    
    @Ann()
    @Ann2(1,2)
    @Ann2(1,3)
    @Ann2(2,4)
    def foo2(): pass
    
    assert list(annotations_of(foo2, instance_of=Ann)) == [Ann()]
    
    # test get
    with pytest.raises(IndexError):
        Ann2.get(foo2, a=1)
    with pytest.raises(ValueError):
        Ann2.get(foo2, a=0)
    assert Ann2.get(foo2, default=0, a=0)==0
    assert Ann.get(foo2) == Ann()
    
    # test annotations_of
    assert len(list(annotations_of(foo2, instance_of=Ann2)))==3
    assert len(list(annotations_of(foo2, instance_of=Ann2, a=1)))==2
    assert len(list(annotations_of(foo2, instance_of=Ann2, a=2)))==1
    assert len(list(annotations_of(foo2, instance_of=Ann2, a=4)))==0    
    assert len(list(annotations_of(foo2, instance_of=Ann2, a=1,b=3)))==1
    assert len(list(annotations_of(foo2, instance_of=Ann2, b=3)))==1
    
    # the same with filter
    assert len(list(Ann2.filter(foo2)))==3
    assert len(list(Ann2.filter(foo2,  a=1)))==2
    assert len(list(Ann2.filter(foo2,  a=2)))==1
    assert len(list(Ann2.filter(foo2,  a=4)))==0    
    assert len(list(Ann2.filter(foo2,  a=1,b=3)))==1
    assert len(list(Ann2.filter(foo2,  b=3)))==1
    
    # the same with has
    assert Ann2.has(foo2)
    assert Ann2.has(foo2,  a=1)
    assert Ann2.has(foo2,  a=2)
    assert not Ann2.has(foo2,  a=4)    
    assert Ann2.has(foo2,  a=1,b=3)
    assert Ann2.has(foo2,  b=3)
    
    class Foo:
        @Ann()
        def meth(self): pass
    
    assert list(annotations_of(Foo.meth)) == [Ann()]
    
    assert Ann2(1,4)==Ann2(1,4)
    assert hash(Ann2(2,4))==hash(Ann2(2,4))
    
    assert Annotatable.for_object("aaa") is None
    assert Annotatable.for_object(Foo) is None
    with pytest.raises(ValueError):
        assert Annotatable.for_object(Foo, throw=True) is None
        
    assert Annotatable.for_object(Foo, create=True) is not None
    
    def bar(): pass
    assert Annotatable.for_object(bar,create=True) is not None
    
    assert Ann2(1,2) == Ann2(b=2, a=1)
    assert Ann2(1,2) == Ann2(a=1, b=2)
    
    assert Ann2(1,2).matches(a=1)
    assert Ann2(1,2).matches(b=2)
    
    assert not Ann2(1,2).matches(b=1)
    assert not Ann2(1,2).matches(a=2)
    
    assert list(Ann.filter(foo2)) == list(annotations_of(foo2, instance_of=Ann))


def test_annotation_equality_semantics():
    A = annotation_class('A',[])
    B = annotation_class('B',[])
    
    assert A()==A()
    assert A() is not A()
    assert A()!=B()
    
    assert hash(A())==hash(A())
    assert hash(B())==hash(B())
    assert hash(A())!=hash(B())
    
    C = annotation_class('C', ['a'])
    D = annotation_class('C', ['a'])
    
    c1 = C(1)
    c2 = C(a=1)
    c3 = C(*(1,))
    c4 = C(*c1)    
    c5 = C(*D(1))
    
    assert c1==c2==c3==c4==c5
    
    assert C(1)!=D(1)
    assert hash(C(1))==hash(C(1))
    assert hash(C(1))!=hash(D(1))
    
    

##############################################################
#
# Example model
#
##############################################################

@model
class Region:
    name = attr(str)
    nations = refs()
    
@model
class Nation:
    name = attr(str)
    region = ref(inv=Region.nations)
    
    citizens = refs()
    addresses = ref()

@model
class Address:
    person = ref()
    street = attr(str)
    zip = attr(str)
    city = attr(str)
    nation = ref(inv=Nation.addresses)
    

@model
class Person:
    name = attr(str)
    
    addresses = refs(inv=Address.person)
    citizen = ref(inv=Nation.citizens)
    
    def __init__(self, name):
        self.name = name
    
@model
class Employee(Person):
    salary = attr(float, 12000.0)
    CheckedConstraint(GREATER_OR_EQUAL(0.0))(salary)
    
    position = attr(str, nullable=True)
    department = ref()
    
    def supervisor(self):
        return self.department.manager
    
@model
class Manager(Employee):
    manages = ref()        

@model
class Department:
    name = attr(str)
    
    employees = refs(inv=Employee.department)        
    manager = ref(inv=Manager.manages)

@model
class Supplier(Person):
    contact_phone = attr(str)
    account_balance = attr(float)
    quotes = refs()
    
@model
class Part:
    name = attr(str)
    manufacturer = attr(str)
    brand = attr(str)
    type = attr(str)
    
    quotes = refs()
    
@model
class SupplierPartQuote:
    part = ref(inv=Part.quotes)
    supplier = ref(inv=Supplier.quotes)    
    
    lineitems = refs()
    
    quantity = attr(float)
    cost = attr(float)
    
@model
class Customer(Person):
    phone = attr(str)
    market = attr(str)
    account_balance = attr(float)
    orders = refs()
    
@model
class Order:
    customer = ref(inv=Customer.orders)
    orderstatus = attr(str)
    totalprice = attr(float)
    lineitems = ref_list()
    
    
@model
class LineItem:
    order = ref(inv=Order.lineitems)
    quote = ref(inv=SupplierPartQuote.lineitems)
    quantity = attr(int)
    price = attr(float)
    discount = attr(float)
    
    

example_model = (Person, Employee, Manager, Department, Supplier, 
                 Nation, Region, Address, Part, SupplierPartQuote, Customer, Order, 
                 LineItem)



def test_validate_example_model_classes():
    from io import StringIO
    with StringIO() as out:
        valid = validate_classes((cls.__model_class__ for cls in example_model), outfile=out) 
        assert valid, "  ERRORS IN VALIDATION OF example_model\n"+out.getvalue()
    

def test_declarative():
        
    def class_check(cls):
        mcls = cls.__model_class__        
        assert mcls.name == cls.__name__
        
        for a in mcls.attributes:
            assert hasattr(cls, a.name)
            
    for cls in example_model:
        class_check(cls)

    cPerson = Person.__model_class__
    cEmployee = Employee.__model_class__
    cManager = Manager.__model_class__
    cDepartment = Department.__model_class__

    assert cPerson.get_attribute('name').type is str
    assert len(list(cPerson.attributes))==1
    assert cPerson.superclasses == ()
    
    assert cEmployee.get_attribute('name').type is str
    assert cEmployee.get_attribute('salary').type is float
    assert cEmployee.get_attribute('position').type is str
    assert cEmployee.get_relationship('department').target is cDepartment
    assert cEmployee.superclasses == (cPerson,)
    
    
    assert cManager.get_attribute('name').type is str
    assert cManager.get_attribute('salary').type is float
    assert cManager.get_attribute('position').type is str
    assert cManager.get_relationship('manages').target is cDepartment
    assert cManager.superclasses == (cEmployee,)

    assert cDepartment.get_attribute('name').type is str
    assert cDepartment.get_relationship('manager').target is cManager
    assert cDepartment.get_relationship('employees').target is cEmployee
    assert cDepartment.get_relationship('employees').kind is RelKind.MANY
        
    assert cDepartment.superclasses == ()
    
    assert cManager.get_attribute('position').type is str


   
def test_example_model():
    
    sales = Department()
    sales.name = 'Sales'
    
    rnd = Department()
    rnd.name = 'R&D'
    
    joe = Employee('Joe')
    joe.department = sales
    joe.position = "Salesman"
    joe.salary = 10000.0

    jack = Employee('Jack')
    jack.department = sales
    jack.position = "Trainee"
    jack.salary = 3000.0
    
    with pytest.raises(ValueError):
        jack.salary = -1000.0  # Not allowed
    assert jack.salary == 3000.0  # We have not touched the old value!
    
    john = Manager('John')
    john.department = sales
    john.position = "Senior salesman"
    john.salary = 15000.0
    john.manages = sales
    
    jill = Manager('Jill')
    jill.department = rnd
    jill.manages = rnd
    jill.position = "Researcher"
    # do not define jill.salary, we will use the default
        
    assert sales.manager is john
    assert len(sales.employees)==3
    total_salary =  sum(x.salary for x in sales.employees)
    assert total_salary == 28000.0
    assert jill.salary == 12000.0
    assert rnd.manager is jill
    assert jill in rnd.employees
    assert jill.name == 'Jill'
    
    with pytest.raises(TypeError):
        jill.salary = "what?"
    
    assert joe.supervisor() is john
    assert jack.supervisor() is john
    assert jill.supervisor() is jill
    
    


@model
class UGNode:
    def __init__(self, n):
        self.node = n
    neighbors = refs(inv=True)


def test_undirected_graph():
    # Test the case where a relationship is with ourselves, a self-relationship.
    # The canonical example is an undirected graph.
    
        
    Graph = list(map(UGNode, range(1,21)))
    assert len(Graph)==20
    
    # Connect relative primes
    from fractions import gcd
    for n1 in Graph:
        for n2 in Graph:
            if n1.node >= n2.node: continue
            if gcd(n1.node, n2.node)==1:
                n1.neighbors.add(n2)
                
    # check connectivity
    def check_connectivity(graph):
        for n1 in graph:
            for n2 in graph:
                assert bool(n1 in n2.neighbors) == bool(n2 in n1.neighbors)
                if n1.node==n2.node: continue 
                assert (n1 in n2.neighbors) == (gcd(n1.node, n2.node)==1)

    check_connectivity(Graph)

    # test self-loop
    n = Graph[0]
    
    assert n not in n.neighbors
    n.neighbors.add(n)
    assert n in n.neighbors
    n.neighbors.remove(n)
    assert n not in n.neighbors
    

    # test that it is picklable
    from pickle import loads, dumps
    
    Graph1 = loads(dumps(Graph))  
    check_connectivity(Graph1)


    n = Graph1[0]
    
    assert n not in n.neighbors
    n.neighbors.add(n)
    assert n in n.neighbors
    n.neighbors.remove(n)
    assert n not in n.neighbors
    



def test_directed_graph():
    
    # Test the case where a relationship is with ourselves, but on different
    # containers. This is testable via a "directed graph" example.
    
    @model
    class DGNode:
        outgoing = refs()
        incoming = refs(inv=outgoing)
    
    # make a rombus
    
    source = DGNode()
    a = DGNode()    
    b = DGNode()
    sink = DGNode()
    
    source.outgoing.add(a)
    source.outgoing.add(b)
    
    a.outgoing.add(sink)
    b.outgoing.add(sink)
    
    
    assert source in a.incoming
    assert source in b.incoming
    assert a in sink.incoming
    assert b in sink.incoming
    assert len(source.incoming)==0
    
    # test for a self-loop
    a.incoming.add(a)
    assert a in a.outgoing
    a.outgoing.remove(a)
    assert a not in a.outgoing
    assert a not in a.incoming
    
    

def test_forward_declarations():
    
    forward = ForwardContext()
    
    @forward
    class Owned1: pass
    
    @forward
    class Owned2: pass
    
    myOwned2 = ForwardProxy(Owned2).ref
    assert myOwned2 is Owned2
    del myOwned2
    
    assert not forward.PENDING
    
    @model
    class Master:
        own1 = ref(inv=Owned1.foo)
        own2 = ref(inv=Owned2.bar)
        attr1 = attr(type=Owned2)
    
    assert forward.PENDING
    
    @model
    class User(Master):
        owner = refs(inv=Owned1.baz)
        attr2 = attr(type=Owned2)

    assert forward.PENDING

        
    assert isinstance(Owned2, ForwardReference)        
    @model
    @forward.define
    class Owned2:
        to1 = ref(inv=Owned1.to2)  # forward
        bar = ref(inv=Master.own2)

    assert isinstance(Owned2, type)            
        
    @model
    @forward.define
    class Owned1(Owned2):   # resolved remaining forwards
        to2 = ref(inv=Owned2.to1)
        foo = ref_list(inv=Master.own1)
        baz = refs(inv=User.owner)
    
    assert not forward.PENDING
    
    all_classes = {Owned1, Owned2, Master, User}
    
    assert validate_classes(cls.__model_class__ for cls in all_classes)
    
    def check_class(cls):
        assert isinstance(cls, type)
        assert hasattr(cls, '__model_class__')
        mcls = cls.__model_class__
        for attr in mcls.all_attributes:
            assert hasattr(cls, attr.name)
            a = getattr(cls, attr.name)
            assert isinstance(a, attr_descriptor)
            assert istypespec(a.content_type)
        for rel in mcls.all_relationships:
            assert hasattr(cls, rel.name)
            r = getattr(cls, rel.name)
            assert isinstance(r, relationship_descriptor)
            assert isinstance(r.content_type, type)
    
    for cls in all_classes:
        check_class(cls)
    
    

def test_inherited_relationships():
    pass
    

def test_dllist():
    @model
    class DLNode:
        def __init__(self, key):
            self.key = key
        key = attr(int)
        prev = ref()
        next = ref(inv=prev)
    
    @model
    class DLList:
        tail = attr(DLNode)
        def __init__(self):
            self.tail = DLNode(-1)
            self.tail.next = self.tail

        @property
        def head(self):
            return self.tail.next
            
        def append(self, key):
            node = DLNode(key)
            node.prev=self.tail.prev
            node.next=self.tail
            
        def prepend(self, key):
            node = DLNode(key)
            node.next=self.head
            node.prev=self.tail
                
        def toList(self):
            L = []
            p = self.head
            while p is not self.tail:
                L.append(p.key)
                p = p.next
            return L
        
        def find(self, k):
            p = self.head
            while p is not self.tail:
                if p.key==k:
                    return p
                p=p.next
            return None
        
        def remove(self, k):
            p = self.find(k)
            p.next.prev = p.prev
            return p
            

    L = DLList()
    assert L.tail is L.head
    assert L.tail is not None
    for i in range(10):
        L.append(i)
    assert L.head is not L.tail
    
    
    D = list(range(10))
    
    assert L.toList() == D
    p=L.remove(0)
    D.remove(0)
    assert p.prev is None
    assert p.next is None
    assert L.toList() == D
    
    L.remove(5)
    D.remove(5)
    assert L.toList() == D
    
    L.remove(9)
    D.remove(9)
    assert L.toList() == D
    

        
class test_validate_core_classes():
    assert validate_classes(CORE_CLASSES)  



#@pytest.skip("To be implemented")    
def test_validate_inherited_references():

    forward = ForwardContext()
    
    @model
    class Base:
        pass
    
    @forward
    class Owner: pass
    
    @model
    class Owned1(Base):
        owner = ref(inv=Owner.owns1)       
    
    @model
    class Owned2(Base):
        owner = ref(inv=Owner.owns2)       
    
    @model
    @forward.define
    class Owner:
        owns1 = ref(target=Owned1, inv=Owned1.owner)
        owns2 = ref(target=Owned2, inv=Owned2.owner)
    
    assert not forward.PENDING
    
    assert validate_classes({Base, Owned1, Owned2, Owner}, outfile=sys.stdout, detail=Validation.FAIL)
    
    joe = Owner()
    house = Owned1()
    car = Owned2()
    
    joe.owns2 = car
    joe.owns1 = house
    
    joe.owns2 = None
    assert car.owner is None

    
if __name__=='__main__':
    test_validate_inherited_references() 



