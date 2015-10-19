'''
Definitions useful for instrumenting model classes.

Created on Oct 24, 2014

@author: vsam
'''
from collections.abc import MutableSet, MutableSequence
from .constraints import is_legal_identifier, Constraint



######################################################
#
#  Model runtime implementation
#
######################################################
    

#
# Exceptions for association error handling
#
class AssociationError(Exception):
    """Base class for association errors."""
    pass

class AssociationTypeError(TypeError, AssociationError):
    """Thrown when the type of object entered in an associative container is not legal"""
    pass

class AssociationDuplicateError(ValueError, AssociationError):
    """Thrown when a duplicate value is inserted in an ordered container."""
    pass

class AssociationNoneError(ValueError, AssociationError):
    """Thrown if None is offered for association to Set or Ordered ."""
    pass




class Associator:
    """Associators are container managers. Each associator is responsible for one side of a relationship.
    
    This class exists mostly for ducumentation purposes, and as a 'void' associator without a peer.
    This is mainly useful for testing, or for using association containers standalone. In the latter
    case, the elements and uniqueness semantics are enforced, but of course there is no actual
    association.
    """
    def __init__(self, content_type):
        """The content_type must be passable as a second argument to isinstance(...)
        """
        self.content_type = content_type
        
    
    def associate(self, own, other):
        """Associate 'own' object with 'other' object.
        
        'own' object must belong to our side of the relationship, 'other' to the other side.
        """
        pass

    def dissociate(self, own, other):
        """Dissociate 'own' object with 'other' object.
        
        'own' object must belong to our side of the relationship, 'other' to the other side.
        """
        pass
       
    def validate_object(self, obj):
        """Validate an object before our side associates with it. 
        
        At a minimum, this must check the object type. The currrent method checks just that.
        """
        if obj is None:
            raise AssociationNoneError("cannot establish association with None")            
        if not isinstance(obj, self.content_type):
            raise AssociationTypeError("object {0} is not a instance of {1}".format(obj, self.content_type))



class PeerAssociator(Associator):
    """This is the implementation of an associator with a peer.
    
    See the documentation of the superclass.
    """
    def __init__(self, peer, content_type, attr_name):
        super().__init__(content_type)
        self.peer = peer
        self.attr_name = attr_name
    


class PeerlessAssociator(PeerAssociator):
    """
    This associator becomes its own peer. It can be used to instantiate
    Association objects without a peer (effectively, standalone containers).

    For example:
    
    S = SetAssociation(None, PeerlessAssociation(int))   
    """
    def __init__(self, content_type):
        super().__init__(self, content_type, None)
    


class Association:
    """This base class provides the behaviour common to all types of association containers.
    """
    
    __slots__=['owner', 'peer_associator']
    
    def __init__(self, owner, peer_associator):
        """Initialize values.
        owner - the hosting object
        associator - 
        """
        self.owner = owner
        self.peer_associator = peer_associator



#
# Containers for maintaining relationships 
# 




# The following is mainly useful for testing

class SingletonAssociation(Association):
    """The singleton container is a pseudo-container that has a maximum
    capacity of 1. It is implemented in the natural way, as an object reference.
    
    N.B. This container is useful primarily because it provides the set and get methods,
    which trigger association mantainance. However, using python descriptors, the
    same effect can be achieved much more cleanly.
    """

    __slots__=['value']
    
    def __init__(self, owner, associator):
        super().__init__(owner, associator)

        self.value = None  # my "container", no association
                
    def set(self, newvalue):
        """Set a new value.
                
        This is the only mutable operation.
        """
        if newvalue is not None:
            self.peer_associator.peer.validate_object(newvalue)   # We need our own associator!
        if self.value is not None:
            self.peer_associator.dissociate(self.value, self.owner)
        self.value = newvalue
        if self.value is not None:
            self.peer_associator.associate(self.value, self.owner)
        
    def get(self):
        """Get the current value.
        """
        return self.value
    
    def __contains__(self, x):
        return self.value is x
    def __iter__(self):
        if self.value is not None:
            yield self.value


class SingletonAssociator(PeerAssociator):
    def associate(self, own, other):
        # symmetric relation check
        if own is other and self.peer is self: return 
        try:
            coll = getattr(own, self.attr_name)
        except AttributeError:
            coll = self.create_container(own)
            setattr(own, self.attr_name, coll)
        if coll.value is other: return
        if coll.value is not None:
            self.peer.dissociate(coll.value, own)
        coll.value = other
    def dissociate(self, own, other):
        # symmetric relation check
        if own is other and self.peer is self: return 
        getattr(own, self.attr_name).value = None

            

#
# Note that this class will be exposed at user level. We don't
# want to make the API too complicated!
#


class  SetAssociation(Association, MutableSet):
    """The set container implements a set of unlimited size. 
    Its implementation uses the MutableSet abstract base class.
    
    TODO: Note that this implementation requires the objects to be
    hashable. A more general implementation based on dicts of object ids,
    would probably be more appropriate.
    """

    __slots__=['values']
    
    def __init__(self, owner, peer_associator):
        super().__init__(owner, peer_associator)
        self.values = set()                    

    def __contains__(self, x):
        return x in self.values
    
    def __len__(self):
        return len(self.values)
    
    def __iter__(self):
        return iter(self.values)

    def add(self, value):
        if value not in self.values:
            self.peer_associator.peer.validate_object(value)
            self.values.add(value)
            self.peer_associator.associate(value, self.owner)
        
    def discard(self, value):
        if value in self.values:
            self.values.discard(value)
            self.peer_associator.dissociate(value, self.owner)
    
    # override to make it fast
    def clear(self):
        for x in self.values:
            self.peer_associator.dissociate(x, self.owner)
        self.values.clear()
    
    def isdisjoint(self, other):
        return self.values.isdisjoint(other)
    
    def assign(self, sobj):
        self.clear()
        for x in sobj:
            self.add(x)

    @classmethod
    def _from_iterable(cls, it):
        return set(it)

    def union(self, other):
        return self.values.union(other)
    
    def __le__(self, other):
        return set.__le__(self.values, other)

    def __repr__(self):
        return "Association(%s) at 0x%x" % (repr(self.values), id(self))
    def __str__(self):
        return "Association(%s)" % str(self.values)
    


class SetAssociator(PeerAssociator):
    """Associator for set associations. 
    
    See the documentation of the superclass for more.
    """
    def associate(self, own, other):
        # symmetric relation check
        if own is other and self.peer is self: return 
        try:
            coll = getattr(own, self.attr_name)
        except AttributeError:
            coll = self.create_container(own)
            setattr(own, self.attr_name, coll)
        coll.values.add(other)
    
    def dissociate(self, own, other):
        # symmetric relation check
        if own is other and self.peer is self: return 
        coll = getattr(own, self.attr_name)
        assert other in coll
        coll.values.remove(other)        
    


#
# Note that this class will be exposed at user level. We don't
# want to make the API too complicated!
#

class  OrderedAssociation(Association, MutableSequence):

    """The ordered container implements a list of unlimited size, with
    set semantics: an associated object can appear only once
    in the list. Also, None is not allowed in the list.
    
    If on operation violates these constraints, an AssociationDuplicate
    """

    __slots__=['seq','values','association_index']
    
    def __init__(self, owner, peer_associator):
        super().__init__(owner, peer_associator)
                
        self.seq = list()
        self.values = set()

        
    def __getitem__(self, index):
        return self.seq[index]
            
    def __len__(self):
        return len(self.values)

    def __setitem__(self, index, newvalue):
        # Check to see if the index is a splice
        if isinstance(index, slice):
            # Check correctness (We should make this as fast as possible)
            if not isinstance(newvalue, set):
                if not isinstance(newvalue, (list,tuple)): 
                    newvalue = list(newvalue)  # we may have an iterator, scan it to preserve order!          
                newvals = set(newvalue)
                if len(newvals)!=len(newvalue):
                    raise AssociationDuplicateError("cannot have duplicates in an association")
            else:
                newvals = newvalue
            
            removed =  set(self.seq[index])
            
            new_not_removed = newvals.difference(removed)            
            removed_not_new = removed.difference(newvals)
            
            if not self.values.isdisjoint(new_not_removed):
                raise AssociationDuplicateError("cannot have duplicates in an association")
                
            # finally, check validity
            valfunc = self.peer_associator.peer.validate_object
            for obj in newvalue:
                valfunc(obj)  # may throw
                
            self.seq[index] = newvalue  # may throw
            self.values.difference_update(removed_not_new)
            self.values.update(new_not_removed)

            for obj in removed_not_new:
                self.peer_associator.dissociate(obj, self.owner)
            for obj in new_not_removed:
                self.peer_associator.associate(obj, self.owner)

            return
        
        else:
            if not isinstance(index, int):
                raise TypeError("Expected int, got {0}".format(index))
    
            # check other errors
            oldvalue = self.seq[index]
            if oldvalue == newvalue: return
            if newvalue in self.values:
                raise AssociationDuplicateError("cannot have duplicates in an association")
            
            self.peer_associator.peer.validate_object(newvalue)
            
            # ok, do it
            self.values.remove(oldvalue)
            self.values.add(newvalue)
            self.seq[index] = newvalue

            self.peer_associator.dissociate(oldvalue, self.owner)
            self.peer_associator.associate(newvalue, self.owner)
            
    
    
    def __delitem__(self, index):
        # Here we support slices!
        U = self.seq[index]
        del self.seq[index]
        if isinstance(index, slice):
            for x in U:
                self.values.remove(x)
                self.peer_associator.dissociate(x, self.owner)
        else:
                self.values.remove(U)
                self.peer_associator.dissociate(U, self.owner)
            
    
    def insert(self, index, newvalue):
        if newvalue in self.values:
            raise AssociationDuplicateError("cannot have duplicates in an association")
        
        self.peer_associator.peer.validate_object(newvalue)
        self.seq.insert(index, newvalue)
        self.values.add(newvalue)        
        self.peer_associator.associate(newvalue, self.owner)
        
    
    def assign(self, sobj):
        self.clear()
        for x in sobj:
            self.append(x)                
        
    # For speed-up, override from MutableList
    def __contains__(self, value):
        return value in self.values

    def sort(self, key=None, reverse=False):
        return self.seq.sort(key=key, reverse=reverse)
        
    def copy(self):
        return self.seq.copy()
    
    def count(self, obj):
        return 1 if obj in self.values else 0
    
    def index(self, *args, **kwargs):
        return self.seq.index(*args, **kwargs)
    
    def reverse(self):
        return self.seq.reverse()

    def __repr__(self):
        return "Association(%s) at 0x%x" % (repr(self.seq),id(self))
    def __str__(self):
        return "Association(%s)" % str(self.seq)

    def __iter__(self):
        return iter(self.seq)



class OrderedAssociator(PeerAssociator):
    """
    Associator for OrderedAssociation.
    
    When an object is associated with the list, it is inserted in a
    position specified by attribute 'association_index'.
    
    This can be a number, in which case a new element is added using
    list.insert(association_index, elem).

    The default is None, in which case, a new element is added by list.append(elem).  
    
    Dissociation is done via list.remove()    
    """
    
    def __init__(self, peer, content_type, attr_name, assoc_index=None):
        super().__init__(peer, content_type, attr_name)
        self.association_index = None
    
    def associate(self, own, other):
        # symmetric relation check
        if own is other and self.peer is self: return 
        try:
            coll = getattr(own, self.attr_name)
        except AttributeError:
            coll = self.create_container(own)
            setattr(own, self.attr_name, coll)
        assert other not in coll.values
        coll.values.add(other)
        if self.association_index is None:
            coll.seq.append(other)
        else:
            coll.seq.insert(self.assoc_index, other)
        
    def dissociate(self, own, other):
        # symmetric relation check
        if own is other and self.peer is self: return 
        coll = getattr(own, self.attr_name)
        assert other in coll
        coll.values.remove(other)
        coll.seq.remove(other)
        
    

#
#  Instrumentation for classes
#

# Some annotations accepted by the instrumentation


class attr_descriptor:  # this is mostly a 'marker' class
    def __init__(self, name, default, nullable, content_type, constraint):
        self.name=name
        self.private_name="__ATTR_%s" % name  # this must be in sync with the generated code
        self.default=default
        self.nullable=nullable
        self.content_type=content_type
        self.constraint=constraint

def attribute_descriptor(name, default=Ellipsis, nullable=True, content_type=object, constraint=None):
    """Return an attribute descriptor for the given arguments.

        This function will return a specially compiled class instance, which hardwires the spec provided
        by the call.
    """

    assert is_legal_identifier(name)
    assert isinstance(nullable, bool)
    #assert istypespec(content_type)

    has_default = default is not Ellipsis
    has_content_type = content_type is not object
    has_constraint = constraint is not None

    # Just in case something is read-only (! to be used later)
    has_setter = True

    if has_constraint and not isinstance(constraint, Constraint):
        constraint = Constraint(constraint,"<for "+name+">")

    path_access = "_ATTR_%s" % name
    #path_access = "__dict__['%s']" % name  # [N.B. for next upgrade]

    def IF(cond, *args): return ''.join(args) if cond else ''

    if isinstance(content_type, tuple):
        typespec = ' or '.join(t.__name__ for t in content_type)
    else:
        typespec = content_type.__name__

    template_text = """
class {{name}}_descriptor(attr_descriptor):

    def initialize(self, obj):
    % if has_default:
        obj.{{path_access}} = self.default
    % else:
        obj.{{path_access}} = Ellipsis
    % end

    % if 1 or has_default:
    def __get__(self, obj, cls):
        try:
            return obj.{{path_access}}
        except (KeyError,AttributeError):
            if obj is None:
                return self
            else:
            % if has_default:
                retval = obj.{{path_access}} = self.default
                return retval
            % else:
                raise AttributeError("object does not have attribute {{name}}")
            % end
    % end

    ## Hard-wire nullable and constraints, for greater speed        
% if has_setter:
    def __set__(self, obj, value):
    % if nullable:
        % if has_content_type or has_constraint:
        if value is not None:
        % end
            % if has_content_type:
            if not isinstance(value, self.content_type):
                raise TypeError("Value is not an instance of {{typespec}}")
            % end
            % if has_constraint:
            self.constraint(value)
            % end
    % else:
        if value is None:
            raise ValueError("attribute is not nullable")
        % if has_content_type:
        if not isinstance(value, self.content_type):
            raise TypeError("Value is not an instance of {{typespec}}")
        %end
        % if has_constraint:
        self.constraint(value)
        % end
    % end
        obj.{{path_access}} = value
%end

    def __delete__(self, obj):
        del obj.{{path_access}}
"""
    from bottle import template
    source = template(template_text, locals(), template_settings={'noescape':True})
    names = dict(globals())
    names.update(locals())
    exec(source, names)
    cls = names[name+"_descriptor"]
    return cls(name, default, nullable, content_type, constraint)



class relationship_descriptor(PeerAssociator):
    PREFIX='REF'
    """Implements the semantics of RelationshipEndpoint access
    """
    def __init__(self, name, target):
        super().__init__(None, target, "__%s_%s" % (self.PREFIX, name))

    def create_container(self, obj):
        raise NotImplementedError()

    def initialize(self, peer):
        self.peer = peer
        
    def __delete__(self, obj):
        raise NotImplementedError("Cannot delete Relationship")
        

class one_relationship_descriptor(relationship_descriptor):
    PREFIX='REF'
    def __init__(self, name, target, read_only=False):
        super().__init__(name, target)

        if read_only:
            self.set = self.read_only_set
        else:
            self.set = self.direct_set

    def __get__(self, obj, cls):
        try:
            return getattr(obj, self.attr_name)
        except AttributeError:
            if obj is None:
                return self
            else:
                setattr(obj, self.attr_name, None)
                return None
    
    def read_only_set(self, obj, value):
        raise AttributeError("Relationship endpoint is read-only")
    
    def direct_set(self, obj, value):
        if value is not None and not isinstance(value, self.content_type):
            raise ValueError("An instance of {0} is expected".format(self.content_type))
        self.associate(obj, value)
        if value is not None:
            self.peer.associate(value, obj)

    def associate(self, obj, value):
        try:
            val = getattr(obj, self.attr_name)
            if val is not None:
                self.peer.dissociate(val, obj)
        except AttributeError:
            pass
        finally:
            setattr(obj, self.attr_name, value)
        
    def dissociate(self, obj, value):
        setattr(obj, self.attr_name, None)
    
    def __set__(self, obj, val):
        self.set(obj, val)   
    

class many_relationship_descriptor(relationship_descriptor):
    PREFIX='REFS'
    def __init__(self, name, target, read_only=False):
        super().__init__(name, target)

    def create_container(self, obj):
        return SetAssociation(obj, self.peer)
                
    def __get__(self, obj, cls):
        try:
            return getattr(obj, self.attr_name)
        except AttributeError:
            if obj is None:
                return self
            ct = self.create_container(obj)
            setattr(obj, self.attr_name, ct)
            return ct
        
    def __set__(self, obj, val):
        return self.__get__(obj, None).assign(val)
    
    associate = SetAssociator.associate
    dissociate = SetAssociator.dissociate

    
class ordered_relationship_descriptor(many_relationship_descriptor):
    PREFIX='REF_LIST'
    def __init__(self, name, target, read_only=False, assoc_index=None):
        super().__init__(name, target, read_only)
        self.association_index = assoc_index
    
    def create_container(self, obj):
        return OrderedAssociation(obj, self.peer)

    associate = OrderedAssociator.associate
    dissociate = OrderedAssociator.dissociate

    

#
#  Transitive closure implementation
#


def transitive_closure(seed, nupath, CHECK=False):
    if isinstance(nupath, RelationshipEndpoint):
        nupath = (nupath,)

    if CHECK:  # maybe we should allow other kinds of sequence?
        assert isinstance(nupath, (tuple, list))

    if len(nupath)==0:
        return seed

    next = [(i+1) % len(nupath) for i in range(len(nupath))]

    if CHECK:  # other checks
        assert all(isinstance(rel, RelationshipEndpoint) for rel in nupath)
        for i in range(nupath):
            r1 = nupath[i]
            r2 = nupath[next[i]]
            assert r1.target is r2.owner

    one = [rel.kind == RelKind.ONE for rel in nupath]
    name = [rel.name for rel in nupath]

    return unchecked_transitive_closure_n(seed, name, one)



def unchecked_transitive_closure_n(seed, name, one):
    from collections import deque
    seen = [set() for _ in range(len(name))]
    next = [(i+1) % len(name) for i in range(len(name))]

    stack = deque()
    for s in seed:
        stack.append((s,0))
        while stack:
            x, i = stack.pop()
            if x not in seen[i]:
                if i==0: yield x   # This can be added here
                seen[i].add(x)
                if one[i]:
                    y = getattr(x,name[i])
                    if y is not None:
                        stack.append((y,next[i]))
                else:
                    for y in getattr(x, name[i]):
                        stack.append((y,next[i]))


def unchecked_acyclic_transitive_closure_1(seed, name):
    while seed:
        yield seed
        seed = getattr(seed, name)

def unchecked_transitive_closure_1(seed, name):
    seen = set({None})
    while seed not in seen:
        seen.add(seed)
        yield seed
        seed = getattr(seed, name)



