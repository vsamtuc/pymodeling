'''
Constraints are a simple library of checks for validating simple attributes in model objects.

Created on Oct 24, 2014

@author: vsam
'''



#
# Constraint checking classes
#



class ConstraintViolation(ValueError):
    """Thrown by Constraint objects when the constraint is not true.
    """
    def __init__(self, constraint, args, kwargs):
        super().__init__(constraint, args, kwargs)
        self.constraint = constraint
        self.call_args = args
        self.call_kwargs = kwargs

    @property
    def message(self):
        msg = "{0} failed".format(self.constraint)
        if len(self.call_args)==1 and len(self.call_kwargs)==0:
            msg += " for {0}".format(repr(self.call_args[0]))
        elif len(self.call_args)+len(self.call_kwargs)>0:
            alist = []
            for a in self.args:
                alist.append(repr(a))
            for k in self.call_kwargs:
                alist.append("{0}={1}", k, repr(self.call_kwargs[k]))
            alist.append(")")
            msgargs = ','.join(alist)
            msg = "{0} for({1})".format(msg,msgargs)
        return msg
    
    def __str__(self):
        return self.message
    
            
class Constraint:
    """A generic callable class for constraints.
    
    A constraint is defined by a predicate (any callable) and an info (a string).
    Constraints can be combined by the &, | and - operator (conjunction, disjunction and negation
    respectively).
    
    Constraints are callable objects. When applied on some arguments, they
    invoke their predicate. If the predicate returns false, a ConstraintViolation is raised.
    Any exceptions thrown by the predicate are propagated.
    """
    
    def __init__(self, func, info="unlabeled"):
        """Create a new constraint.
        func - a callable that implements the check
        info - a string describing the check
        """
        if not callable(func):  raise  TypeError("A callable is expected for func")
        if not isinstance(info, str):  raise  TypeError("A string is expected for info")
        self.func=func
        self.info=info

    def __call__(self, *args, **kwargs):
        """Call func with given args.
        If the result is false, raise ConstraintViolation
        """
        if not self.func(*args, **kwargs):
            raise ConstraintViolation(self, args, kwargs)

    def negated(self):
        """Return a new Constraint object with negated semantics."""
        
        func = lambda *args, **kwargs: not self.func(*args, **kwargs)
        info = ("NOT "+self.info) if self.info!="unlabeled" else "unlabeled"
        return Constraint(func, info)

    def __neg__(self):
        """Return self.negated()"""
        return self.negated()

    def __or__(self, other):
        """Return a Constraints object for the disjunction of self and other."""
        if isinstance(other, Constraint):
            return Constraints(self, other, any=True)
        else:
            return Constraints(self, Constraint(other), any=True)
    
    def __and__(self, other):
        """Return a Constraints object for the conjunction of self and other."""
        if isinstance(other, Constraint):
            return Constraints(self, other)
        else:
            return Constraints(self, Constraint(other))
        
    def __str__(self):
        return "Constraint({0})".format(self.info)
    
    def __repr__(self):
        cls = type(self)
        return "<{0}.{1} object '{2}' at {3:x}>".format(cls.__module__, cls.__name__, self.info, id(self))
    


class Constraints(Constraint):
    """This is a simple class to aggregate constraints.
    
    Constraints are aggregated either conjunctively or disjunctively.
    It takes care of several issues, such as constructing a composite info message
    from all info messages.
    """
    
    def __init__(self,  *args,  any=False):
        """Initialize a Constraints object with a sequence of args.
        If any is True, the aggregate constraint is the disjunction of the
        operands, else it is the conjunction (default).
        """
        self.constraints = []
        self.__any = any
        self.__func = None
        self.__info = None
        for a in args:
            self.add(a)
        
    def __changed(self):
        self.__func = None
        self.__info = None
        
    @property 
    def info(self):
        def paren(label):
            if " AND " in label  or  " OR " in label:
                return "(%s)" % label
            else:
                return label

        if self.__info is None:
            infos = [paren(c.info) for c in self.constraints]
            # parenthesize as needed
            conn = " OR " if self.any else " AND "
            self.__info = conn.join(infos)
        return self.__info
    
    @property
    def any(self):
        return self.__any

    @property
    def func(self):
        if self.__func is None:
            # Create an optimized function
            if len(self.constraints)==0:
                if self.any:
                    self.__func = lambda *args, **kwargs: False
                else:
                    self.__func = lambda *args, **kwargs: True
            elif len(self.constraints)==1:
                self.__func = self.constraints[0].func
            else:
                if self.any:
                    self.__func = lambda *args, **kwargs: any(c.func(*args, **kwargs) for c in self.constraints)
                else:
                    self.__func = lambda *args, **kwargs: all(c.func(*args, **kwargs) for c in self.constraints)
            
        return self.__func
    
    def add(self, c, info=None):
        if isinstance(c, Constraints) and self.any==c.any:
            self.constraints.extend(c.constraints)
        elif isinstance(c, Constraint):
            self.constraints.append(c)
        elif callable(c):
            if info is not None:
                self.constraints.append(Constraint(c, info))
            elif hasattr(c, '__name__'):
                self.constraints.append(Constraint(c, c.__name__))
            else:
                self.constraints.append(Constraint(c))
        else:
            raise TypeError("Cannot add non-callable")
        self.__changed()
                
    def __all(self, *args, **kwargs):
        for constraint in self.constraints:
            constraint(*args, **kwargs)
      
    def __any(self, *args, **kwargs):
        for c in self.constraints:
            if success(c, *args, **kwargs):
                return True
        raise ConstraintViolation(self, args, kwargs)
    
    def negated(self):
        negc = Constraints(any=not self.any)
        for c in self.constraints:
            negc.add(c.negated())
        return negc
        
    def __iter__(self):
        return iter(self.constraints)


#
#  Schema validation
#


def success(constr, *args, **kwargs):
    """Return ``False`` if the call ``constr(*args, **kwargs)`` raises ``ConstraintViolation``, 
    else return ``True``. Other exceptions raised by ``constr`` are propagated.
    """
    try:
        constr(*args, **kwargs)
        return True
    except ConstraintViolation:
        return False



# specialization for constraints classes


NULL = Constraint(lambda x: x is None, "null")
NONNULL = Constraint(lambda x: x is not None, "not null")

class HAS_TYPE(Constraint):
    def __init__(self, *types):
        info = "instance of " + (" or ".join(t.__name__ for t in types))
        super().__init__(lambda x: isinstance(x,types), info)
        self.types = types

class BETWEEN(Constraint):
    def __init__(self, a,b):
        info = "between {0} and {1}".format(a,b)
        super().__init__(lambda x: (x>=a) and (x<=b), info)
        self.low = a
        self.high = b

class GREATER(Constraint):
    def __init__(self, val):
        super().__init__(lambda x: x>val, "greater than {0}".format(val))
        self.value = val
    def negated(self):
        return LESS_OR_EQUAL(self.value)

class GREATER_OR_EQUAL(Constraint):
    def __init__(self, val):
        super().__init__(lambda x: x>=val, "greater than or equal to {0}".format(val))
        self.value = val
    def negated(self):
        return LESS(self.value)

class LESS(Constraint):
    def __init__(self,val):
        super().__init__(lambda x: x<val, "less than {0}".format(val))
        self.value = val
    def negated(self):
        return GREATER_OR_EQUAL(self.value)

class LESS_OR_EQUAL(Constraint):
    def __init__(self,val):
        super().__init__(lambda x: x<=val, "less than or equal to {0}".format(val))
        self.value = val
    def negated(self):
        return GREATER(self.value)

class LENGTH(Constraint):
    def __check_lengths(self, maximum, minimum):
        if not (maximum is None or isinstance(maximum, int)):
            raise TypeError("int or None expected")
        if not (minimum is None or isinstance(minimum, int)):
            raise TypeError("int or None expected")
        if maximum is None and minimum is None:
            raise ValueError("length limits are both None")
        if not (maximum is None or minimum is None or maximum>=minimum):
            raise ValueError("incompatible length limits")

    def __init__(self, maximum=None, minimum=None):
        self.__check_lengths(maximum, minimum)
        
        info_list = []
        if minimum is not None: info_list.append("at least {0}".format(minimum))
        if maximum is not None: info_list.append("at most {0}".format(maximum))
        info = "length is "+" and ".join(info_list)
        
        if minimum is None:
            func = lambda x: len(x)<=maximum
        elif maximum is None:
            func = lambda x: len(x)>=minimum
        else:
            func = lambda x: minimum <= len(x) <= maximum
            
        super().__init__(func, info)
        self.minimum = minimum
        self.maximum = maximum


def HAS_ATTR(*attr):
    if len(attr)>1:
        info = "has attributes " + (','.join(attr))
    elif len(attr)==1:
        info = "has attribute {0}".format(attr[0])
    else:
        info = "true"
    return Constraint(lambda x: all(hasattr(x,a) for a in attr) , info)

def MISSING_ATTR(a):
    return Constraint(lambda x: not hasattr(x,a), "missing attribute {0}".format(a))

def NOT(c):
    if not isinstance(c, Constraint): raise TypeError("Constraint expected")
    return c.negated()


def is_legal_identifier(name):
    import keyword 
    import re
    return isinstance(name, str) and re.match("[_A-Za-z][_a-zA-Z0-9]*$",name) \
                and not keyword.iskeyword(name) 

LEGAL_IDENTIFIER = Constraint(is_legal_identifier, "is legal identifier")

CALLABLE = Constraint(callable, "is callable")

