'''
Created on Oct 24, 2014

@author: vsam
'''
from modeling.instrument import Associator, SingletonAssociation, SetAssociation,\
    OrderedAssociation, AssociationDuplicateError, attribute_descriptor,\
    one_relationship_descriptor, many_relationship_descriptor,\
    ordered_relationship_descriptor, SingletonAssociator, SetAssociator,\
    OrderedAssociator, PeerlessAssociator, attr_descriptor
import pytest


#
#
#  Testing associated containers
#
#

def test_assert_associated_containers_have_no_dict():
    
    # This is not really a test, just a generic assertion
    class Node:
        def __init__(self, assoc):
            self.container = assoc(self, Associator(Node))

    
    s1 = Node(SingletonAssociation).container
    s2 = Node(SetAssociation).container
    s3 = Node(OrderedAssociation).container
    assert not hasattr(s1,'__dict__')
    assert not hasattr(s2,'__dict__')
    assert not hasattr(s3,'__dict__')



def test_SetAssociation():
    
    S = SetAssociation(None, PeerlessAssociator(int))
    
    S.assign({1,2,3})
    
    assert len(S)==3
    assert S == {1,2,3}
    assert S | {4,5} == {1,2,3,4,5}
    assert S & {1,4,6} == {1}    
    assert set(S) == {1,2,3}
    assert S.isdisjoint({0})
    assert S.isdisjoint(set())
    




#
# Create a pair of classes for relationships of this kind
#

def create_associated_classes(kind1, kind2):
    Container = { 
                 'ONE': SingletonAssociation,
                 'MANY': SetAssociation,
                 'ORDERED': OrderedAssociation
                }
    Assoc = { 
                 'ONE': SingletonAssociator,
                 'MANY': SetAssociator,
                 'ORDERED': OrderedAssociator                
            }

    
    class Node:            
        def __repr__(self):
            return "<{0}(container={1}) at {2:x}>".format(self.__class__.__name__, self.kind, id(self))
        def check_invariant(self):
            for x in self.container:
                assert self in x.container

    class Node1(Node):
        kind = kind1
        def __init__(self):
            self.container = Container[self.kind](self, self.peer_associator)
            
    class Node2(Node):
        kind = kind2
        def __init__(self):
            self.container = Container[self.kind](self, self.peer_associator)
            
        
    
    assoc1 = Assoc[kind1](None, Node2, 'container')
    assoc2 = Assoc[kind2](assoc1, Node1, 'container')
    assoc1.peer = assoc2

    Node1.peer_associator = assoc2
    Node2.peer_associator = assoc1
    
    return Node1, Node2
    


def test_association_one_to_one():

    Node1, Node2 = create_associated_classes('ONE', 'ONE')

    nodesA = [Node1() for i in range(20)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
    
    # run 1000 random assignments
    for it in range(1000):
        na = choice(nodesA)
        nb = choice(nodesB)
        nc = choice(nodesA)
        
        # make one association and one dissociation
        na.container.set(nb)
        assert na.container.get() is nb
        assert nb.container.get() is na
        nc.container.set(None)
        
        # assert the invariant on all nodes
        for n in nodesA:
            n.check_invariant()
        for n in nodesB:
            n.check_invariant()
            
            
def test_association_one_to_many():    
    

    Node1, Node2 = create_associated_classes('ONE', 'MANY')
        
    nodesA = [Node1() for i in range(20)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
    
    # run 1000 random assignments
    for it in range(1000):
        # Make changes on randomly selected containers
        choice(nodesA).container.set(choice(nodesB))
        choice(nodesA).container.set(None)
               
        choice(nodesB).container.add(choice(nodesA))
        choice(nodesB).container.discard(choice(nodesA))
        
        
        # assert the node invariant
        for n in nodesA:
            n.check_invariant()
        for n in nodesB:
            n.check_invariant()


def test_association_many_to_many():    
    
    Node1, Node2 = create_associated_classes('MANY', 'MANY')
        
    nodesA = [Node1() for i in range(30)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
    
    # run 1000 random assignments
    for it in range(1000):
        # Make changes on randomly selected containers
        choice(nodesA).container.add(choice(nodesB))
        choice(nodesA).container.discard(choice(nodesB))
               
        choice(nodesB).container.add(choice(nodesA))
        choice(nodesB).container.discard(choice(nodesA))
        
        # assert the node invariant
        for n in nodesA:
            n.check_invariant()
        for n in nodesB:
            n.check_invariant()


#
# We are not allowed to insert and remove random elements
# (insert would cause duplicate errors, remove is not like discard!)

def append_random_element(L, S):
    from random import choice
    e = choice(S)
    if e not in L:
        L.append(e)

def insert_random_element(L, S):
    from random import choice, randint
    e = choice(S)
    if e not in L:
        pos = randint(0,len(L))
        L.insert(pos,e)

def remove_random_element(L):
    from random import choice
    if len(L)>0:
        x = choice(L)
        L.remove(x)

def test_association_one_to_ordered():    
    
    Node1, Node2 = create_associated_classes('ONE', 'ORDERED')    
        
    nodesA = [Node1() for i in range(20)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
    
    # run 1000 random assignments
    for it in range(1000):
        # Make changes on randomly selected containers
        choice(nodesA).container.set(choice(nodesB))
        choice(nodesA).container.set(None)
               
        append_random_element(choice(nodesB).container, nodesA)
        insert_random_element(choice(nodesB).container, nodesA)
        remove_random_element(choice(nodesB).container)
        
        
        # assert the node invariant
        for n in nodesA:
            n.check_invariant()
        for n in nodesB:
            n.check_invariant()


def test_association_many_to_ordered():    

    Node1, Node2 = create_associated_classes('MANY', 'ORDERED')        
        
    nodesA = [Node1() for i in range(30)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
        
    # run 1000 random assignments
    for it in range(1000):
        # Make changes on randomly selected containers
        choice(nodesA).container.add(choice(nodesB))
        choice(nodesA).container.discard(choice(nodesB))
               
        append_random_element(choice(nodesB).container, nodesA)
        insert_random_element(choice(nodesB).container, nodesA)
        remove_random_element(choice(nodesB).container)

        # test clearing
        nb = choice(nodesB)
        nb.container.clear()
        assert len(nb.container)==0
        
        # assert the node invariant
        for n in nodesA:
            n.check_invariant()
        for n in nodesB:
            n.check_invariant()


def test_association_ordered_to_ordered():    

    Node1, Node2 = create_associated_classes('ORDERED', 'ORDERED')            
        
    nodesA = [Node1() for i in range(30)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
    
    # invariants for node 
    def check_invariant(node):
        assert set(node.container.seq)==node.container.values
        node.check_invariant()
    
    # run 1000 random assignments
    for it in range(1000):
        # Make changes on randomly selected containers
        insert_random_element(choice(nodesA).container, nodesB)
        remove_random_element(choice(nodesA).container)
               
        append_random_element(choice(nodesB).container, nodesA)
        remove_random_element(choice(nodesB).container)
        
        # assert the node invariant
        for n in nodesA:
            check_invariant(n)
        for n in nodesB:
            check_invariant(n)


def test_association_ordered_to_ordered_indexing():

    Node1, Node2 = create_associated_classes('ORDERED', 'ORDERED')            
        
    nodesA = [Node1() for i in range(30)]
    nodesB = [Node2() for i in range(10)]
    
    from random import choice
    
    # invariants for node 
    def check_invariant(node):
        assert len(node.container.seq) == len(node.container.values)
        assert set(node.container.seq) == node.container.values
        node.check_invariant()
    
    # run 1000 random assignments
    for it in range(1000):
        # Make changes on randomly selected containers
        insert_random_element(choice(nodesA).container, nodesB)
        remove_random_element(choice(nodesA).container)
               
        append_random_element(choice(nodesB).container, nodesA)
        remove_random_element(choice(nodesB).container)

        na = choice(nodesA)
        na.container[:] = []
        assert len(na.container) == 0
        check_invariant(na)
        
        na.container[:] = nodesB
        assert len(na.container) == len(nodesB)
        check_invariant(na)
        
        # assert the node invariant
        for n in nodesA:
            check_invariant(n)
        for n in nodesB:
            check_invariant(n)


    # swap half the container
    na = choice(nodesA)
    L = na.container
    A = L[0:5]
    del L[0:5]
    L.extend(A)
    check_invariant(na)
    
    L.sort(key=id)
    check_invariant(na)
    
    with pytest.raises(AssociationDuplicateError):
        L += nodesB      
    
    # assert the node invariant
    for n in nodesA:
        check_invariant(n)
    for n in nodesB:
        check_invariant(n)
    

    


def test_attribute_descriptor1():
    assert not hasattr(attribute_descriptor('name', default=10), "check")
    
    class Foo:
        name = attribute_descriptor("name", default=10, content_type=int, 
                                 nullable=False, constraint=lambda x: x%10==0)
        
    x = Foo()
    assert x.name == 10
    
    x.name = 30
    assert x.name == 30
    
    with pytest.raises(ValueError):
        x.name = 3
    with pytest.raises(TypeError):
        x.name = "asdas"
    with pytest.raises(TypeError):
        x.name = 3.4
    with pytest.raises(ValueError):
        x.name = None
    del x.name
    assert x.name==10  # back to the default value

def test_attribute_descriptor2():
    class Foo:
        a = attribute_descriptor("name", default=10, content_type=int, 
                                 nullable=True, constraint=lambda x: x%10==0)
                
    x = Foo()
    assert x.a == 10
    
    x.a = 30
    assert x.a == 30

    x.a = None
    assert x.a is None
    
    with pytest.raises(ValueError):
        x.a = 3
    with pytest.raises(TypeError):
        x.a = "asdas"
    with pytest.raises(TypeError):
        x.a = 3.4
        

def test_attribute_descriptor_type_union():
    class Foo:
        x = attribute_descriptor("x", default=10, 
                                 content_type=(int,float), 
                                 nullable=True)
        
    obj = Foo()
    
    obj.x = 1
    assert isinstance(obj.x, int)
    assert not isinstance(obj.x, float)
    obj.x = 1.0
    assert isinstance(obj.x, float)
    assert not isinstance(obj.x, int)



def test_relationship_descriptor_one_to_one():
    
    class Man:
        pass
    
    class Woman:
        pass 

    # configure
    Man.wife = one_relationship_descriptor('wife', Woman)
    Woman.husband = one_relationship_descriptor('husband', Man)
    Man.wife.initialize(Woman.husband)
    Woman.husband.initialize(Man.wife)
    
            
    mark = Man()
    
    tom = Man()
    
    mary = Woman()
    sally = Woman()
    
    assert mark.wife is None
    assert tom.wife is None
    assert mary.husband is None
    
    mark.wife = mary
    assert mary.husband is mark
    assert mark.wife is mary
    assert tom.wife is None
    
    sally.husband = tom
    assert tom.wife is sally
    
    mark.wife = sally
    assert mary.husband is None
    assert tom.wife is None
    assert mark.wife is sally 
    assert sally.husband is mark
    
    sally.husband = None
    assert tom.wife is None
    assert mark.wife is None

    with pytest.raises(ValueError):
        tom.wife = 1


def test_relationship_descriptor_one_to_many():
    class Entry:
        def __init__(self,name):
            self.name = name
        def __repr__(self):
            if self.parent:
                return repr(self.parent)+"/"+self.name
            else:
                return self.name
    class Directory(Entry):
        pass
    class File(Entry):
        pass
    
    Entry.parent = one_relationship_descriptor('parent', Directory)
    Directory.contents = many_relationship_descriptor('contents', Entry)
    Entry.parent.initialize(Directory.contents)
    Directory.contents.initialize(Entry.parent)
    
    root = Directory("")
    etc = Directory("etc")
    usr = Directory("usr")
    mnt = Directory("mnt")
    var = Directory("var")
    root.contents.add(etc)
    root.contents.add(usr)
    root.contents.add(mnt)
    root.contents.add(var)

    root.contents = []
    assert len(root.contents)==0
    root.contents = [mnt,var]
    assert len(root.contents)==2
    root.contents.add(etc)
    root.contents.add(usr) 
    assert len(root.contents)==4

    assert etc.parent == usr.parent == mnt.parent == var.parent == root

    pwd = File("pwd")
    pwd.parent=etc
    bin, lib, man = Directory("bin"), Directory("lib"), Directory("man")
    bin.parent = man.parent = lib.parent = usr
    assert usr.contents == set([bin, man, lib])
    
    var.contents.add(lib)
    assert lib.parent == var
    assert lib in var.contents
    assert lib not in usr.contents
    
    etc.contents.add(File("f1"))
    etc.contents.add(File("f2"))
    etc.contents.add(File("f3"))

    with pytest.raises(TypeError):
        etc.contents.add(15)
    with pytest.raises(ValueError):
        etc.contents.add(None)
    with pytest.raises(TypeError):
        etc.contents.add("adsada")
    with pytest.raises(KeyError):
        etc.contents.remove(15)
    etc.contents.discard(14)
    
    
def test_relationship_descriptor_many_to_many():
    class User:
        pass
    class Group:
        pass
    Group_users = many_relationship_descriptor('users', User)
    User_groups = many_relationship_descriptor('groups', Group)
    Group_users.initialize(User_groups)
    User_groups.initialize(Group_users)
    Group.users = Group_users
    User.groups = User_groups 
    
    groups = [Group() for i in range(10)]
    users = [User() for i in range(10)]
    
    from random import choice
    
    def check_group_invariant(group):
        for user in group.users:
            assert group in user.groups
    
    for i in range(1000):
        choice(users).groups.add(choice(groups))
        choice(groups).users.discard(choice(users))
        
        for g in groups:
            check_group_invariant(g)


def test_relationship_descriptor_one_to_ordered():
    class Entry:
        parent=None
    class Directory(Entry):
        contents=None
    class File(Entry):
        pass
    
    Entry_parent = one_relationship_descriptor('parent', Directory)
    Directory_contents = ordered_relationship_descriptor('contents', Entry)
    Entry_parent.initialize(Directory_contents)
    Directory_contents.initialize(Entry_parent)

    Entry.parent = Entry_parent
    Directory.contents = Directory_contents
    
    root = Directory()
    etc = Directory()
    usr = Directory()
    mnt = Directory()
    var = Directory()
    root.contents.append(etc)
    root.contents.append(usr)
    root.contents.append(mnt)
    root.contents.append(var)
    
    root.contents = []
    assert len(root.contents)==0
    root.contents = [etc,usr,mnt,var]
    assert len(root.contents)==4

    assert etc.parent == usr.parent == mnt.parent == var.parent == root
    assert list(root.contents) == [etc, usr, mnt, var]

    pwd = File()
    pwd.parent=etc
    bin, lib, man = Directory(), Directory(), Directory()
    bin.parent = man.parent = lib.parent = usr
    assert list(usr.contents) == [bin, man, lib]
    
    var.contents.append(lib)
    assert lib.parent == var
    assert lib in var.contents
    assert lib not in usr.contents
    
    etc.contents.append(File())
    assert len(etc.contents)==2
    pwd.parent = var
    assert len(etc.contents)==1
    
    with pytest.raises(ValueError):
        etc.contents.append(None)        
    with pytest.raises(TypeError):
        etc.contents.append(15)
    with pytest.raises(TypeError):
        etc.contents.append("adsada")
    with pytest.raises(ValueError):
        etc.contents.remove(15)
    

def test_attribute_codegen():

    class Foo:
        a = attribute_descriptor('a', content_type=int, nullable=False)

    x = Foo()

    with pytest.raises(AttributeError):
        x.a

    with pytest.raises(ValueError):
        x.a = None

    assert isinstance(Foo.a, attr_descriptor)

def test_attribute_timeit():
    from timeit import repeat

    setup = """
from modeling.instrument import attribute_descriptor
class Foo:
    def __init__(self):
        Foo.a.initialize(self)

    a = attribute_descriptor('a', content_type=int, nullable=False)

x = Foo()
x.a=1
x.b=10
    """

    t1 = min(repeat("x.a", setup=setup))
    t2 = min(repeat("x.b", setup=setup))
    print("Instrumented timing:", t1)
    print("Direct       timing:", t2)

