'''
The forward facility is a callback framework that allows models to be expressed 
more naturally.

Created on Oct 24, 2014

@author: vsam
'''
from weakref import WeakValueDictionary
from .constraints import is_legal_identifier


class ForwardContext:
    """This class provides the context for a tree of ForwardReference objects."""

    def __init__(self):
        self.TOPLEVEL = WeakValueDictionary()
        self.PENDING = set()    # set of references with pending callbacks
    
    
    def get_name(self, obj):
        """
        Return a name for the given object.
        
        Strings are named for themselves.
        
        Objects with an attribute '__name__', (e.g. classes, functions and modules) have its
        value as attribute.
        
        Otherwise, a NameError is raised.
        
        Subclasses can override this method to customize its behaviour.  
        """
        if isinstance(obj, str):
            return obj
        if hasattr(obj, '__name__'):
            return obj.__name__
        raise NameError("Cannot obtain name for object",obj)
    
    def __call__(self, obj):
        """Return (and, if needed, create) a ForwardReference for the name of the given object.
        
            The function returns a "root" ForwardReference for the name of the given object.
        """
        name = self.get_name(obj)
        if name in self.TOPLEVEL:
            raise NameError("Name %s is already defined in this context")
        ref = ForwardReference(name, self)
        self.TOPLEVEL[name] = ref
        return ref
    
    def define(self, obj, name=None):
        """
        Invoke the callback for a "root" ForwardReference.
        
        The name of the reference is either provided in argument 'name', or (if null)
        is computed from get_name(). 
        """
        # get a name
        if name is None:
            name = self.get_name(obj)
        else:
            name = self.get_name(name)
        
        # bind the element
        self.TOPLEVEL[name](obj)
        
        # return the obj
        return obj


class ForwardReference:
    """A simple registry of forward references of classes.
    
    Objects can attach themselves to these objects to document association
    to future declarations. 
    
    DO NOT attempt to access the attribute of such an object directly (!!)
    or you will just receive back a new ForwardReference instance.
    __getattribute__ bites (!!)
    
    Application code should NEVER need to dereference ForwardReference objects,
    except of course for creating new references.
    
    USE THE proxy: you can get it via an uderscore "attribute"
    
    x = ForwardReference(....)
    
    x._.name 
    x._.context
    
    """
    
    __slots__ = ('context', 'parent', 'name', 'children', 'callbacks', '__weakref__')

    def __init__(self, name, parent):

        G = object.__getattribute__
        
        if not isinstance(name, str) or (isinstance(parent, ForwardReference) and not is_legal_identifier(name)):
            raise ValueError("ForwardReference name must be a legal identifier name, not "+name)
        
        self.name = name
        
        if not isinstance(parent, (ForwardReference, ForwardContext)):
            raise ValueError("Either a ForwardReference or a ForwardContext must be provided")
        if isinstance(parent, ForwardReference):            
            self.parent = parent
            self.context = G(parent, 'context')
        else:
            self.parent = None
            self.context = parent

        assert name not in (G(G(self,'parent'),'children') if G(self,'parent') else G(self,'context').TOPLEVEL)
        
        self.children = WeakValueDictionary()
        self.callbacks = []
            
    def __getattribute__(self, name):
        """Return a child ForwardReference with the given name. Note that if a child with this name
        exists, it is returned. Else, a new reference is returned.
        
        As a special case, attribute '_' will return a proxy for this reference.
        """
        if name=='_':                  # quick access to a proxy.
            return ForwardProxy(self)
        G = object.__getattribute__
        if name in G(self,'children'):
            return G(self, 'children')[name]
        else:
            child = ForwardReference(name, self)
            G(self,'children')[name] = child
            return child

    def attach(self, callback):
        """Add a callable to the callback list."""
        G = object.__getattribute__
        if not G(self,'callbacks'):   # make ourselves strongly referenced!
            G(self,'context').PENDING.add(self)
        G(self,'callbacks').append(callback)
    
    def __call__(self, value, idx=None):
        """Bind a value to this reference. 
        
           If this value is not a ForwardReference, then:
           (a) invoke all callbacks on this reference and its children,
           (b) remove all callbacks from the callback list and the global callback set.
           (c) become 'bound'. In the future, all attach calls will be rejected with an exception.
           
           If the value is a forward reference, then this implementation will attach itself the 
           new reference, as a callable itself.
        """
        G = object.__getattribute__
        if isinstance(value, ForwardReference):
            G(value,'attach')( (self, None) )
            # do not propagate to children
        else:
            # invoke own callbacks 
            for callback in G(self,'callbacks'):
                func, index = callback
                func(value, index)
            # propagate to children
            for child in G(self,'children'):
                child_value = getattr(value, child)
                G(self,'children')[child](child_value)
            # clear callbacks
            G(self,'callbacks').clear() 
            G(self,'context').PENDING.discard(self)  # we need not be strongly referenced any more!

    def __repr__(self):
        G = object.__getattribute__
        namelist = []
        p = self
        while p is not None:
            namelist.append(G(p,'name'))
            p = G(p,'parent')
        namelist.reverse()
        return '.'.join(namelist)
    
    def __str__(self):
        return "Forward(%s)" % repr(self)



class ForwardProxy:
    """Helper class to handle ForwardReference objects (without creating names!) """

    def __init__(self, fwref):
        """
        This method initializes a proxy for a ForwardReference (or, more simply, a reference)
        in different ways.
        
        It takes as argument a ForwardReference, or a ForwardContext
        
        If the argument is a ForwardReference, it initializes a proxy for it. The argument is known
        as the proxied reference.

        If it is a ForwardContext, the proxy can be used to access
        the 'toplevel' references still in use. Only attributes 'context', 'toplevel' and 'pending' 
        and the indexing operation are allowed on the proxy (e.g.  x['Topname']) 
        """        
        if not isinstance(fwref, (ForwardReference, ForwardContext)):
            raise ValueError("A ForwardReference or ForwardContext was expected, got %s" % fwref)
        self.__fwref = fwref

    @property
    def toplevel(self):
        return self.context.TOPLEVEL
    
    @property
    def pending(self):
        return self.context.PENDING
    
    def __getitem__(self, idx):
        """Indexing returns a proxy to one of the children of the proxied reference by name.
        
        A KeyError is thrown if there is no child by this name.
        """
        path = idx.split('.')
        G = object.__getattribute__
        if isinstance(self.__fwref, ForwardContext):
            root = self.toplevel
        else:
            root = G(self.__fwref, 'children')
        for child in path:
            obj = root[child]
            root = G(obj, 'children')
        return ForwardProxy(obj)
            
    def __get(self, attr):
        assert attr in ['name','parent','children','context','callbacks', 'attach']\
             and isinstance(self.__fwref, ForwardReference)
        return object.__getattribute__(self.__fwref, attr)

    @property
    def name(self):
        """The name of the proxied reference"""
        return self.__get('name')
    @property
    def children(self):
        """A list of proxies for the children of the proxied reference."""
        return [ForwardProxy(child) for child in self.__get('children').values()]
    
    @property
    def parent(self):
        """A proxy to the parent of the proxied reference"""
        parent = self.__get('parent')
        if parent:
            return ForwardProxy(parent)
        else:
            return parent
    
    @property
    def context(self):
        """The ForwardContext of the proxied reference"""
        if isinstance(self.__fwref, ForwardContext):
            return self.__fwref
        else:
            return self.__get('context')
    
    @property
    def callbacks(self):
        """A proxy to the callback list of the proxied reference"""
        return self.__get('callbacks')
    
    @property
    def ref(self):
        """The proxied reference or context itself. Use with care..."""
        return self.__fwref

    def attach(self, func, index=None):
        """Attach the given callable to the proxied reference."""
        if isinstance(self.__fwref, ForwardContext):
            raise RuntimeError("Cannot attach: no proxied reference in this proxy")
        self.__get('attach')( (func,index) )
        
    def bind_value(self, value):
        """Bind a value to a forward reference. 
        
        This will trigger all callbacks for the reference and its children.
        """
        if isinstance(self.__fwref, ForwardContext):
            raise RuntimeError("Cannot attach: no proxied reference in this proxy")
        self.__fwref(value)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__fwref is other.__fwref

    def __hash__(self, other):
        return hash(self.__fwref) + hash(self.__class__)

    def __repr__(self):
        return "<proxy of %s>" % self.__fwref

##############################################

#
#  Callbacks
#         

class forward_call:
    """Instances define forward function calls.
    
    In the constructor, pass a function and positional and/or keyword arguments.
    An argument may be a callback, i.e., a ForwardReference or another forward_call,
    or any other object.
    
    When all callbacks have triggered, the instance applies 'func' to all its
    (concrete) arguments and invokes its own callbacks (if any), propagating the
    result of the call to 'func'.

    Example use:
    
    forward = ForwardContext()
    
    A = forward('A')
    
    
    b = MyObject()
    
    
    forward_call(setattr, b, 'foo', forward_call(len, A.list_of_items))
    
    
    A = forward.define(myA, 'A')  # myA has attribute 'list_of_items'
    
    assert b.foo == len(myA.list_of_items)
    
    
    """
    
    __slots__ = ('barrier', 'callbacks', 'func', 'slots', 'kwslots', 'result')

    def __init__(self, func, *slots, **kwslots):
        """Construct a forward call.
        
        func - any callable
        slots - positional arguments
        kwslots - keyword arguments
        """
        
        self.barrier = 1
        self.callbacks = []
        self.func = func
                
        self.slots = list(slots)
        forward_store = self.__forward_store
        
        storeslot = self.__storeslot
        for i in range(len(slots)):
            forward_store(storeslot, self.slots, i, slots[i])

        storekwslot = self.__storekwslot
        self.kwslots = kwslots        
        for k in kwslots:
            forward_store(storekwslot, kwslots, k, kwslots[k])

        self.barrier -= 1
        if self.barrier==0:
            self.__barrier_run()
            
    def __storeslot(self, value, loc):
        self.slots[loc] = value
        self.barrier -= 1
        if self.barrier==0:
            self.__barrier_run() 
        
    def __storekwslot(self, value, loc):
        self.kwslots[loc] = value
        self.barrier -= 1
        if self.barrier==0:
            self.__barrier_run() 
        
    def __forward_store(self, func, O, K, V):
        if isinstance(V, ForwardReference):
            self.barrier += 1
            V._.attach(func, K)
        elif isinstance(V, forward_call):
            if hasattr(V, 'result'): # it is ready
                O[K] = V.result
            else:                
                self.barrier += 1
                V.__attach(func, K)

    def __barrier_run(self):
        self.result = self.func(* tuple(self.slots), ** self.kwslots)
        while self.callbacks:
            self.__emit(self.callbacks.pop())
    
    def __attach(self, func, idx=0):
        callback = (func, idx)
        if hasattr(self, 'result'):
            self.__emit(callback)
        else:
            self.callbacks.append(callback)
            
    def __emit(self, callback):
        func, index = callback
        func(self.result, index)


class forward_invoke:
        
    def __init__(self, ref, call, *args, **kwargs):
        self.call = call
        self.args = args
        self.kwargs = kwargs
        ref._.attach(self)
    def __call__(self, value, index):
        self.call(* self.args, ** self.kwargs)


def forward_setattr(obj,attr,ref):
    """Wrapper for forward call
    """
    forward_call(setattr, obj, attr, ref)

