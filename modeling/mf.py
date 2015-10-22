'''
Modeling framework.

This library defines a simple framework for Model Driven Programming in Python.

Created on Sep 28, 2014

@author: vsam
'''


from enum import Enum
from inspect import getattr_static
from collections import namedtuple

from .constraints import Constraint, Constraints
from .constraints import is_legal_identifier, ConstraintViolation,\
    LEGAL_IDENTIFIER
from .forward import ForwardReference, forward_setattr, forward_invoke
from .validation import Validation
from .instrument import attribute_descriptor, relationship_descriptor,\
    one_relationship_descriptor, many_relationship_descriptor,\
    ordered_relationship_descriptor



#
#  Annotations
#
class Annotation:
    """Base class for annotation classes created by `annotation_class`.
    
    Examples::
    
        # create an annotation class
        Ann = annotation_class('Ann', [])
        
        # annotate function
        @Ann()
        def myfunc(): pass
        
        # annotate class
        @Ann()
        class myclass: pass
        
        # create annotation class with two attributes
        Position = annotation_class('Position', ['x', 'y'])
        
        # annotate function
        @Posistion(2,3)
        def foo(): ...
        
        # same as above
        @Position(y=3, x=2)
        def foo(): ...
        
        # get an annotation instance
        pos23 = Position(2,3)
        
        # annotate with this annotation
        @pos23
        def foo(): ...
        
        # create a subclass of Annotatable 
        class MyClass(Annotatable): pass
        
        # create Annotatable object
        x = MyClass()
        
        # annotate the object
        pos23(x)
        
    """
    def __call__(self, obj):
        """Annotate obj with this annotation.
        
        obj must be an instance of Annotatable, or a type or a function.
        
        This method allows annotation instances to be used as decorators.
        """
        able = Annotatable.for_object(obj, create=True, throw=True)
        able._Annotatable__add_annotation(self)
        return obj

    def __eq__(self, other):
        return type(self) is type(other) and super().__eq__(other)
    
    def __ne__(self, other):
        return not(self == other)
    
    def __hash__(self):
        return hash(type(self))+super().__hash__() 

    def matches(self, **kwargs):
        """Check if the ``kwargs`` match the fields of this annotation.
        
        Example:
        ::
            
            Point = annotation_class('Point', ['x', 'y'])        
            
            Point(1,2).matches(x=1) -> True
            Point(1,2).matches(y=1) -> False 
        
        :param kwargs: Keywords that define the query.
        :return: A boolean value indicating match.
        """
        for arg in kwargs:
            if not hasattr(self, arg) or not (getattr(self, arg)==kwargs[arg]):
                return False
        return True
    
    
    @classmethod
    def filter(cls, obj, **kwargs):
        """Generator returning all annotations from ``obj``'s Annotatable,
        which are instances of ``cls`` and match ``kwargs``.
        """
        for a in Annotatable.for_object(obj, create=False, throw=True).annotations:
            if isinstance(a,cls) and a.matches(**kwargs):
                yield a

    @classmethod
    def get(cls, obj, default=Ellipsis, **kwargs):
        """Get the unique annotation of type ``cls`` in the annotatable of ``obj``.
        
        If there is no such annotation, then if ``default`` is provided, return the 
        ``default``, else raise a ``ValueError``.

        If there are more than 1 annotations, raise ``IndexError``.
        """
        I = cls.filter(obj, **kwargs)
        assert hasattr(I,'__next__')
        
        item=None
        try:
            item = next(I)
            next(I)
            raise IndexError("Mutliple annotations of type {0} exist".format(cls.__name__))            
        except StopIteration:
            pass

        if item is None:        
            if default is not Ellipsis:
                return default
            else:
                raise ValueError("No annotations of type {0} exist".format(cls.__name__))
        return item

    @classmethod
    def get_item(cls,obj, item=0, default=Ellipsis, **kwargs):
        """Return some ``item`` (by default item 0) of an annotation found
        by calling ``get(obj, **kwargs)``.
        
        If no annotation of this type exists on ``obj``, and ``default`` is provided,
        then ``default`` is returned.
        
        On all other error cases, the raised exception (by get) is passed through.
        """
        try:
            return cls.get(obj, **kwargs)[item]
        except ValueError:
            if default is Ellipsis:
                raise
            else:
                return default
        
    @classmethod
    def has(cls, obj, **kwargs):
        """Return True iff obj has some annotation of type cls, matching kwargs.
        """
        try:
            next(cls.filter(obj, **kwargs))
            return True
        except StopIteration:
            return False


def annotation_class(typename, field_names):
    """Create a new annotation class.
    """
    tuplename = "namedtuple_"+"_".join(field_names)
    ancls = namedtuple(tuplename, field_names)
    return type(typename, (Annotation, ancls), {})



class Annotatable:
    """An Annotatable object maintains a list of :py:class:`~modeling.mf.Annotation` objects.
    """
    
    def __init__(self):
        self.__ann = list()
    
    @property
    def annotations(self):
        """Property returning an iterator over all annotations for this object."""
        yield from self.__ann

    def __add_annotation(self, ann):
        if not isinstance(ann, Annotation):
            raise TypeError("Annotation expected")
        self.__ann.insert(0, ann)
    
    @staticmethod
    def for_object(obj, create=False, throw=False):
        """Return an :py:class:`~modeling.mf.Annotatable` instance for ``obj``.

        If ``obj`` is an instance of :py:class:`~modeling.mf.Annotatable`, this returns ``obj`` itself.

        If ``obj`` is a type, or a function (including unbound methods), this
        call looks up attribute ``__annotatable__``, as described below. If not,
        then if ``throw`` is ``True`` a :py:class:`TypeError` is raised, else ``None`` is returned.
        
        If ``obj.__annotatable__`` exists and points to an instance of :py:class:`~modeling.mf.Annotatable`,
        then ``obj.__annotatable__`` is returned.
        
        If ``obj.__annotatable__`` exists but is not an instance of :py:class:`~modeling.mf.Annotatable`,
        if ``throw`` is ``True``, a TypeError is raised, else ``None`` is returned.
        
        If ``obj.__annotatable__`` does not exist, then:

        * if ``create`` is ``True``, ``obj.__annotatable__`` is bound to a new 
          :py:class:`~modeling.mf.Annotatable` object and this object is returned.

        * if ``create`` is ``False``, then if ``throw`` is ``True``, a ValueError is raised, else,
          ``None`` is returned.

        :param object obj: The object for which an :py:class:`~modeling.mf.Annotatable` is returned.
        """
        
        import types
        try:
            if isinstance(obj, Annotatable): 
                return obj
            if isinstance(obj, (type, types.FunctionType)):
                if hasattr(obj,"__annotatable__"):
                    able = getattr(obj,"__annotatable__")
                    if not isinstance(able, Annotatable):
                        raise TypeError("obj.__annotatable__ is not of type mf.Annotatable!")
                else:
                    if create:
                        able = Annotatable()
                        setattr(obj, "__annotatable__", able)
                    else:
                        raise ValueError("obj does not have an Annotatable")
            else:
                raise TypeError("obj is neither Annotatable nor a function or a type")
            return able
        except:
            if throw:
                raise
            return None
        

def annotations_of(obj, instance_of=Annotation, **kwargs):
    """Query the list of annotations of an object.

        Return every annotation ``x`` of ``obj``, 
        where ``isinstance(x,instance_of)`` and
        ``x.matches(kwargs)``.

        :param object obj: The object whose list of annotations is returned.
        :param Annotation instance_of: A subclass of :py:class:`~modeling.mf.Annotation` used to match
          annotations.
        :param kwargs: Keywords passed to :py:meth:`modeling.mf.Annotation.matches`.
        :return: An iterator over the matched annotations.
    """
    # N.B. instance_of 
    able = Annotatable.for_object(obj, create=False, throw=False)
    if able is None: return
    assert isinstance(able, Annotatable)
    yield from instance_of.filter(able, **kwargs)


###################################################
#
#  Core modeling classes
#
###################################################


def istypespec(t):
    """Check if the argument is a proper type specification.

    A typespec can be one of the following:
    * any Python type.
    * any mf.Class instance.
    * a tuple of the above, designating alternatives (a "type union").


    Arguments:
    t -- The value checked to be a proper typespec.
    """
    def istype(x):
        return isinstance(x, type) or isinstance(x, Class)
    if isinstance(t, tuple):
        return all(istype(e) for e in t)
    else:
        # TODO: We do not allow ForwardReference in a tuple, but should!
        return istype(t)


    
#
#  Main entities
#


class NamedEntity(Annotatable):
    """A named entity has a single Attribute, "name".
    
    It must be a legal python identifier.
    """

    def __init__(self,name):
        """Initialize with given name, which should be a string."""
        super().__init__() 
        self.name=name
    
    @property
    def name(self):
        """The name of the entity."""
        return self.__name
    @name.setter
    def name(self, name):
        if name is not None and not is_legal_identifier(name):
            raise ValueError("Illegal python identifier: {0}".format(name))
        self.__name = name

        
class ClassFeature(NamedEntity):
    """A model element which properly belongs to a class.
    
    This class is a superclass for Attributes and RelationshipEndpoints.
    """
    def __init__(self, name, owner):
        super().__init__(name) 
        self.owner = owner
    
    @property
    def owner(self):
        return self.__owner
    @owner.setter
    def owner(self, newowner):
        if newowner is not None and not isinstance(newowner, Class):
            raise TypeError("An mf.Class instance was expected, got {0}".format(newowner))
        self.__owner = newowner



class Attribute(ClassFeature):
    """Class attribute model.
    """

    def __init__(self, name=None, owner=None, type=object, default=Ellipsis, nullable=False):
        """Initialize an attribute.
        
        name - must be a legal python identifier, or None (to be bound later, or
             several methods raise an exception).
        type - can be any type object or a mf.Class or a forward declaration, or a non-empty tuple whose elements 
             are types or mf.Classes or forward decalarations. 
        default - Ellipsis (in greek means "being without") denotes
             a non-defaultable Attribute, None or any value denotes itself
        nullable - a boolean, denotes whether None is allowed
        """
        super().__init__(name, owner)
        self.type=type
        self.nullable=nullable
        self.default=default

        if owner is not None:
            owner.add_attribute(self)
        
    @property
    def type(self):
        """This is either a """
        return self.__type
    @type.setter
    def type(self, typ):
        if isinstance(typ, ForwardReference):
            forward_setattr(self, 'type', typ)
            self.__type = typ
        elif not istypespec(typ):
            raise TypeError("A type or a forward reference is expected, got {0}".format(typ))
        else:    
            self.__type=typ
    
    @property
    def default(self):
        return self.__default
    @default.setter
    def default(self, default):
        if not (default is Ellipsis or default is None or isinstance(default, self.type)):
            raise TypeError("Expected Ellipsis, None, or an object of type {0}".format(self.type.__name__))
        self.__default = default
        
    @property
    def nullable(self):
        return self.__nullable
    @nullable.setter
    def nullable(self, nullable):
        if not isinstance(nullable, bool):
            raise TypeError("A boolean is expected.")
        self.__nullable=nullable

    def __repr__(self):
        return "mf.Attribute(name={0}.{1}, type={2}, default={3}, nullable={4})"\
        .format(self.owner.name, self.name, self.type.__name__, str(self.default), self.nullable)


    
class Class(NamedEntity):
    """
    Class model.

    An mf.Class (to be distinguished from python classes) is defined by
      * an iterable of superclasses (which could be None or empty), 
      * a set of attributes 
      * a set of relationships
    
    Note: we are talking about multiple inheritance and have no 'Object' class!
    This is much like C++ virtual inheritance. Also, we use the python MRO to
    order all superclasses.
    """
    def __init__(self, name=None, superclasses=None, attributes=set()):
        super().__init__(name)
        
        # superclasses is an iterable of mf.Class objects of python classes
        # adorned witht the __model_class__ attribute, which must evaluate to
        # an mf.Class.

        sclist = []
        if superclasses is None:
            superclasses = ()
        for c in superclasses:
            C = c
            if not isinstance(C, Class) and hasattr(C,'__model_class__'):
                C = c.__model_class__
            if not isinstance(C,Class):
                raise TypeError("Each superclass must be an mf.Class instance or have attribute __model_class__, got %s" % c)
            sclist.append(C)

        self.__superclasses = tuple(sclist)


        
        self.__attributes = set(attributes)
        for attr in self.__attributes:
            if attr.owner is None:
                attr.owner = self
            elif attr.owner is not self:
                raise ValueError("attribute with owner set to another class was given")
        
        self.__relationships = set()
               
    @property
    def superclasses(self):
        return self.__superclasses
    
    
    def is_subclass(self, other):
        if not isinstance(other, Class):
            raise TypeError("An mf.Class was expected")
        cur = self
        while cur is not None:
            if cur is other: return True
            cur = cur.__superclass
        return False
        
    def is_superclass(self, other):
        return other.is_subclass(self)
    
    def all_superclasses(self):
        yield from self.all_proper_superclasses()
        yield self
        
    def all_proper_superclasses(self):
        sc = self.superclass
        while sc is not None:
            yield sc
            sc = sc.superclass
    
    # superclass cannot be changed after construction. 
    # This way, we avoid cycles in the inheritance graph!
    # Also, since we have single inheritance, we need not mess with the MRO!
    
    @property
    def attributes(self):
        """Return only the attributes defined in this class."""
        yield from self.__attributes
    
    @property
    def all_attributes(self):
        """Return visible attributes defined in this class and its superclasses
             N.B. in the current implementation, all attributes are visible
        """
        if self.superclass is not None:
            yield from self.superclass.all_attributes
        yield from self.__attributes
    
    @property
    def relationships(self):
        """Return only the relationship endpoints defined in this class."""
        yield from self.__relationships

    @property
    def all_relationships(self):
        """Return visible relationship endpoints defined in this class and its superclasses.
            N.B. in the current implementation, all relationships are visible
        """
        if self.superclass is not None:
            yield from self.superclass.all_relationships
        yield from self.__relationships
    

    def add_attribute(self, *args, **kwargs):
        """
        Add an Attribute to this mf.Class.
        
        This function can be called in two ways:
        (a) a single, non-keyword argument of type Attribute, and no
        other arguments, positional or keyword.
        (b) any number of positional and keyword arguments.
        
        In case (a), the given Attribute object is added to this class.
        In case (b), the arguments are passed verbatim to the constructor
        of class Attribute, and the resulting object is then added.
        """
        if len(args)==1 and len(kwargs)==0 and isinstance(args[0], Attribute):
            attr = args[0]
        else:
            attr = Attribute(*args, **kwargs)
        
        if attr.owner not in (None,self):
            raise ValueError("Attribute with a different owner was passed")
        attr.owner = self
        self.__attributes.add(attr)
        return attr

    def add_relationship(self, rel):
        """
        Add a RelationshipEndpoint to this mf.Class.
        """
        if not isinstance(rel, RelationshipEndpoint):
            raise TypeError("A RelationshipEndpoint was expected")
        rel.owner = self
        self.__relationships.add(rel)
        return rel


    def get_attribute(self, name):
        """Get an attribute by name or raise a KeyError.
        """
        for a in self.attributes:
            if a.name==name:
                return a
        if self.superclass is not None:
            return self.superclass.get_attribute(name)
        raise KeyError("Class has no attribute {0}".format(name))
        
    def get_relationship(self, name):
        """Get an relationship by name or raise a KeyError.
        """
        for a in self.relationships:
            if a.name==name:
                return a
        if self.superclass is not None:
            return self.superclass.get_relationship(name)
        raise KeyError("Class has no attribute {0}".format(name))

        
    def __repr__(self):
        """Return a repr string containing the class name.
        """
        return "<mf.Class('{0}') at {1:x}>".format(self.name, id(self))




class RelKind(Enum):
    """Relationship endpoint kind.
    
    Used to denote 1:1, 1:m, etc. relationships.
    ORDERED implies MANY (naturally!)
    """
    ONE=1,
    MANY=2
    ORDERED=3



class RelationshipEndpoint(ClassFeature):
    """Relationship endpoint model.

    A relationship is a constraint on object attributes that hold references
    to other objects.

    Let C1 and C2 be classes, and  C1.r1, C2.r2 be members, such that 
    C1.r1 is a singleton or collection of references to instances of C2, and
    C2.r2 is a singleton or collection of references to instances of C1. The
    relationship invariant demands that,

    given x1 an instance of C1, and x2 an instance of C2,
    x2 belongs to x1.r1, if and only if, x1 belongs to x2.r2

    When C1==C2 and r1==r2, the relationship is *symmetric*.

    A non-symmetric relationship is defined by a pair of RelationshipEndpoint
    instances, called peers.

    A symmetric relationship is modeled by a single RelationshipEndpoint
    instance.

    """

    def __init__(self, name=None, owner=None, target=None, kind=None, peer=None):
        super().__init__(name, owner)

        if owner is not None:
            owner.add_relationship(self)
        
        if target is None or isinstance(target, Class):
            self.__target=target
        elif isinstance(target, ForwardReference):
            forward_setattr(self, 'target', target)
        else:
            raise TypeError("Class expected")
        
        if kind is not None and not isinstance(kind, RelKind):
            raise TypeError("RelKind expected")
        self.__kind=kind
        
        self.__peer=None
        if peer is None:
            pass

        elif isinstance(peer, RelationshipEndpoint):
            assert peer.__peer is None
            self.__peer=peer
            peer.__peer = self

        elif isinstance(peer, ForwardReference):
            forward_setattr(self, 'peer', peer)

        else:
            assert isinstance(peer, tuple)
            pname, powner, ptarget, pkind = peer
            self.__peer = RelationshipEndpoint(pname, powner, ptarget, pkind, self)
            
    
    @property
    def target(self):
        return self.__target
    @target.setter
    def target(self, target):
        if not isinstance(target, Class):
            raise TypeError("mf.Class expected.")
        self.__target = target
    
    @property
    def kind(self):
        return self.__kind
    @kind.setter
    def kind(self, kind):
        if not isinstance(kind, RelKind):
            raise TypeError("RelKind expected")
        self.__kind = kind
    
    @property
    def peer(self):
        return self.__peer
    @peer.setter
    def peer(self, peer):
        if not isinstance(peer, RelationshipEndpoint):
            raise TypeError("RelationshipEndpoint expected")
        self.__peer = peer




def relationships(C1, rel1, kind1, C2, rel2, kind2):
    """Create a pair of relationships.
    
    Semantics: let isinstance(x1,C1) and isinstance(x2,C2) then
       x1.rel1  points to x2   iff    x2.rel2  points to x1 
    """
    r1 = RelationshipEndpoint(rel1, C1, C2, kind1, (rel2, C2, C1, kind2))
    r2 = r1.peer
    return r1, r2


def symmetric_relationship(C, rel, kind):
    r = RelationshipEndpoint(rel, C, C, kind, None)
    r.peer = r
    return r


#
# Declarative model construction API
#


def attr(type=object, default=Ellipsis, nullable=True):
    """Return a nameless Attribute instance for binding to some class attribute.
    
    class Foo:
       myfield = attr(str, nullable=False)
    """
    return Attribute(type=type, default=default, nullable=nullable)

#
# Annotations for attributes
#

# This annotation carries an integrity check that the instrumentation
# will attach to the attribute setter.
# The check will not be made when attempting to set the value to None 
# (of course, the attribute must be nullable, or an error wlll be raised).
CheckedConstraint = annotation_class('CheckedConstraint', ['check'])

# TODO: This is currently unsupported!
ReadOnly = annotation_class('ReadOnly', [])()



#  Private helper
def _ref_create(target, inv, kind):
    assert isinstance(kind, RelKind)
    
    if not (target is None or isinstance(target, (Class, ForwardReference))):
        if hasattr(target, '__model_class__'):
            target = target.__model_class__
        else:
            raise ValueError("Target must be an mf.Class, or a modeled python class or a forward reference")
    
    if inv is None:
        return RelationshipEndpoint(target=target, kind=kind)
    elif isinstance(inv, (RelationshipEndpoint, ForwardReference)):
        return RelationshipEndpoint(target=target, kind=kind, peer=inv)
    elif inv is True:
        ret = RelationshipEndpoint(target=target, kind=kind)
        ret.peer = ret
        return ret
    else:
        raise TypeError("inv must be a RelationshipEndpoint") 


def ref(target=None, inv=None):
    """Return a nameless :py:class:`~modeling.mf.RelationshipEndpoint` instance for binding to 
    some class attribute.
    
    If ``inv`` is provided and is an instance of :py:class:`~modeling.mf.RelationshipEndpoint`, 
    then peer this :py:class:`~modeling.mf.RelationshipEndpoint` to the given one.
    
    If ``inv`` is ``True``, then define a self-relationship (a symmetric relationship).
    
    The ``RelKind`` is ``ONE``.
    ::    
    
        class Foo:
            myguest = ref()
        ...
        class Bar:
            myhost = ref(inv=Foo.myguest)
    """
    return _ref_create(target, inv, RelKind.ONE)

def refs(target=None, inv=None):
    """Return a nameless RelationshipEndpoint instance for binding to some class attribute.
    If inv is provided and is an instance of RelationshipEndpoint,
    then peer this RelationshipEndpoint to the given one.
    If inv is True, then define a self-relationship (a symmetric relationship).

    The RelKind is MANY.
        
    class Person:
        parent = ref()
        children = refs(inv=parent)
        
    class UndirectedGraphNode:
        neighbors = refs(int=True)
        ...
    """
    return _ref_create(target, inv, RelKind.MANY)

def ref_list(target=None, inv=None):
    """Return a nameless :py:class:`~modeling.mf.RelationshipEndpoint`
    instance for binding to some class attribute.

    If ``inv`` is provided and is an instance of :py:class:`~modeling.mf.RelationshipEndpoint`, 
    then peer this :py:class:`~modeling.mf.RelationshipEndpoint` to the given one.
    
    If ``inv`` is ``True``, then define a self-relationship (a symmetric relationship).

    The ``RelKind`` is ``ORDERED``.
    ::
    
        class TableRow:
            table = ref()
        ...
        class Table:
             rows = ref_list(inv=TableRow.table)
    """
    return _ref_create(target, inv, RelKind.ORDERED)


#
#
#

class ModelExtractionError(ConstraintViolation):
    pass


python_type = annotation_class('python_type', ('type'))


def model(cls):
    """This method is applied on a python class in order to:
    
    #. extract a model from the class and 
    #. instrument the class, together with other classes, as needed  
    """
    mcls = extract_model(cls)
    instrument_class(cls, mcls)
    return cls
    


def set_model_class(cls, mcls):
    """Set the model class of ``cls`` to be ``mcls``.

    This method will check that ``cls`` is actually a type and that
    attribute ``__model_class__`` is not yet defined.
    """

    if not isinstance(cls, type):
        raise TypeError("A python class was expected")
    if "__model_class__" in vars(cls):
        raise ValueError("The class object already has attribute '__model_class__'")
    
    cls.__model_class__ = mcls
    python_type(cls)(mcls)


def model_class(cls):
    """Return the model class of ``cls``.
    """
    if isinstance(cls, Class):
        return cls
    else:
        return cls.__model_class__
    


def extract_model(cls):
    """Return a :py:class:`~modeling.mf.Class` from a python class.
    """

    name = cls.__name__
    
    # get superclass
    sc = [bc  for bc in cls.__bases__ if hasattr(bc, '__model_class__')]
    if not (0<= len(sc) <=1):
        scn = [s.__name__ for s in sc]
        raise ModelExtractionError("Multiple direct super-classes found: {0}".format([scn]))
    superclass = sc[0].__model_class__ if len(sc)>0 else None
    
    # create model class
    mcls = Class(name, superclass)

    # model class feature extraction
    D = vars(cls)
    for ename in D:
        elem = D[ename]
        
        if isinstance(elem, Attribute):
            mcls.add_attribute(elem)
            if elem.name is None:
                elem.name=ename
                
        elif isinstance(elem, RelationshipEndpoint):
            mcls.add_relationship(elem)
            if elem.name is None:
                elem.name = ename                

        else:
            pass

    for elem in mcls.relationships:            
        # fix relationships
        if elem.peer is not None:
            # Fix the dependencies
            if elem.peer.name is None:
                raise ModelExtractionError("Relationship peer is unnamed for {0}".format(ename))
            
            elem.peer.target = mcls            
            elem.target = elem.peer.owner
            
            assert elem.peer.peer is elem
            assert elem.peer.kind is not None
            assert elem.kind is not None
                
    # all went well, complete the class assignment
    set_model_class(cls, mcls)    
    return mcls


#
#  Class instrumentation
#

class InstrumentationError(Exception):
    pass


def instrument_attribute(cls, attr):
    
    # if the attribute class is a future, set a callback on its value and return
    if isinstance(attr.type, ForwardReference):
        forward_invoke(attr.type, instrument_attribute, cls, attr)
        return
    
    # compute the attribute constraint from annotations
    clist = [cann.check for cann in CheckedConstraint.filter(attr)]
    if not all(isinstance(check, Constraint) for check in clist):
        raise InstrumentationError("CheckedConstraint.check is not a Constraint, in attribute {0} of class {1}",attr,cls)
    if clist:
        constraint = clist[0] if len(clist)==1 else Constraints(*clist)
    else:
        constraint = None
    
    desc = attribute_descriptor(attr.name, attr.default, attr.nullable, attr.type, constraint)
    setattr(cls, attr.name, desc)



def instrument_relationship(cls, rel):
    assert isinstance(rel, RelationshipEndpoint)
    assert rel.name is not None

    # check if this relationship is already instrumented
    if isinstance(getattr_static(cls, rel.name), relationship_descriptor):
        return

    # If the relationship has not been built yet, we leave the RelationsipEndpoint
    # itself in the attribute. When the peer is instrumented, this endpoint 
    # will also be instrumented.
    if rel.peer is None:
        assert getattr(cls, rel.name) is rel
        return

    # Else, we have a peer, so we instrument both sides, if needed

    # A utility function for creation of descriptors
    def create_descriptor(kind, name, target, owner):        
        if kind is RelKind.ONE:
            desc = one_relationship_descriptor(name, target, read_only=False)
        elif kind is RelKind.MANY:
            desc = many_relationship_descriptor(name, target, read_only=False)
        elif kind is RelKind.ORDERED:
            desc = ordered_relationship_descriptor(name, target, read_only=False)
        else:
            raise ValueError("Cannot instrument for this relationship kind: {0}".format(kind))
        setattr(owner, name, desc)
        return desc

    
    if rel.peer is rel:
        # We have a symmetric relationship, just instrument it
        d = create_descriptor(rel.kind, rel.name, cls, cls)
        d.initialize(d)
        
    else:
        # we have to instrument both sides
        ocls = python_type.get(rel.target).type
        assert getattr(ocls, rel.peer.name) is rel.peer
    
        # the descriptor for rel
        d = create_descriptor(rel.kind, rel.name, ocls, cls)
        # the descriptor for rel peer
        od = create_descriptor(rel.peer.kind, rel.peer.name, cls, ocls)
            
        d.initialize(od)
        od.initialize(d)
    
        
def instrument_class(cls, mcls):
    # bind attributes

    # Alternative attribute instrumentations:
    # (1) Do nothing, simply remove the Attribute
    #   and perhaps define the class attribute with the default (if any)
    #
    # Another option might be to define a suitable "__setattr__"
    # and leave attribute "get" as is. This would make it
    # very fast.
    

    for attr in mcls.attributes:
        instrument_attribute(cls, attr)

    # instrument relationships    
    for rel in mcls.relationships:
        instrument_relationship(cls, rel)


#
#  Validation for model classes
#       


class ClassValidation(Validation):
    """This validation validates Class, Relationship and Attribute objects.
    It can be used most conveniently via function validate_classes().
    
    This is useful when the Class objects are constructed by hand.
    """

    def validate_model_class(self, cls, validset):
        # return if already checked
        if validset is not None and cls in validset:
            return True
        
        if not (cls.superclass is None):
            isvalid = self.validate_model_class(cls.superclass, validset)
            if validset is not None:
                validset[cls] = isvalid
            
        with self.section("Class '{0}'", cls.name) as V:            

            # check if it has a name
            V(cls.name is not None, "Class has a name")
            
            # check if the superclass is valid
            if validset is not None and cls.superclass is not None:
                V(validset[cls.superclass], "Superclass is valid")
                
            
            # check that Attribute names are nonnul and unique
            attr_names = [a.name for a in cls.attributes]
            s_attr_names = set(attr_names)

            V(None not in attr_names, "Every attribute is named")
            V(len(s_attr_names) == len(attr_names), "Attribute names are distinct")
                       
            # check that RelationshipEndpoint names are nonnul and unique
            rel_names = [r.name for r in cls.relationships]
            s_rel_names = set(rel_names)
            V(None not in rel_names, "Every relationship is named")
            V(len(s_rel_names) == len(rel_names), "Relationship names are distinct")
            
            # check that Attribute and RelationshipEndpoint names are unique
            V(s_attr_names.isdisjoint(s_rel_names), "Attribute and relationship names are distinct")
        
            # check that we are not hiding any inherited RelationshipEndpoint name
            irn = set()
            for psc in cls.all_proper_superclasses():
                irn = irn.union({r.name for r in psc.relationships})
            local_names = s_attr_names.union(s_rel_names)
            
            V(irn.isdisjoint(local_names), "Inherited relationship names are not hidden")
            
            for attr in cls.attributes:
                self.validate_attribute(cls, attr)
                
            for rel in cls.relationships:
                self.validate_relationship(cls, rel)
             
            if validset is not None:
                validset[cls] = V.passed_section()
                
            return V.passed_section()
            
    
    def validate_attribute(self, cls, attr):
        with self.section("Attribute '{0}'", attr.name) as V:
            V(attr.owner is cls, "Attribute owner is the class.")
            
            
    def validate_relationship(self, cls, rel):
        with self.section("RelationshipEndpoint '{0}'", rel.name) as V:
            V(rel.owner is cls, "Relationship endpoint owner is the class")
            V(rel.peer is not None, "Peer is not none")
            if rel.peer is not None:
                V(rel.peer.peer is rel, "Peer's peer is self")
                V(rel.peer.owner is rel.target, "Target is peer's owner")
                


def validate_classes(S, **kwargs):
    vld = ClassValidation(**kwargs)
    validset = {}
    Sclasses = [model_class(c) for c in S]
    for cls in Sclasses:
        if cls not in validset:
            isvalid = vld.validate_model_class(cls, validset)
            validset[cls]=isvalid
    return vld.passed()
    


#
# The mf CORE model classes
#

CORE_CLASSES=[]
class _CORE:
    # We use a class to avoid messing up the namespace.
    # It is deleted after it is used!
    
    mAnnotatable = Class('Annotatable',None)
    mAnnotatable.add_attribute(name='annotations', type=set)
        
    set_model_class(Annotatable, mAnnotatable)
        
    mNamedEntity = Class('NamedEntity', mAnnotatable)
    a = mNamedEntity.add_attribute(name='name', type=str, default=None)
    CheckedConstraint(LEGAL_IDENTIFIER)(a)
    
    set_model_class(NamedEntity, mNamedEntity)
    
    mClassOwned = Class('ClassFeature', mNamedEntity)
    owner = mClassOwned.add_attribute(name='owner')

    set_model_class(ClassFeature, mClassOwned)
    
    mAttribute = Class('Attribute', mClassOwned)
    mAttribute.add_attribute(name='type', type=(type, tuple), nullable=False, default=object)
    mAttribute.add_attribute(name='default', type=object, nullable=True, default=Ellipsis)
    mAttribute.add_attribute(name='nullable', type=bool, nullable=False, default=False)

    set_model_class(Attribute, mAttribute)
    
    mClass = Class('Class', mNamedEntity)
    mClass.add_attribute(name='superclass', type=mClass, default=None)
    mClass.add_attribute(name='attributes', type=set)
    mClass.add_attribute(name='relationships', type=set)
    
    set_model_class(Class, mClass)
    owner.type = mClass

    mRelationshipEndpoint = Class('RelationshipEndpoint', mClassOwned)
    mRelationshipEndpoint.add_attribute(name='target', type=mClass)
    mRelationshipEndpoint.add_attribute(name='kind', type=RelKind)
    #mRelationshipEndpoint.add_attribute(name='peer', type=mRelationshipEndpoint)
    symmetric_relationship(mRelationshipEndpoint, 'peer', RelKind.ONE)

    set_model_class(RelationshipEndpoint, mRelationshipEndpoint)


    global CORE_CLASSES
    CORE_CLASSES = [mAnnotatable, mNamedEntity, mClassOwned,
              mClass, mAttribute, mRelationshipEndpoint]



del _CORE

