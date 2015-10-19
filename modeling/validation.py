'''
Created on Oct 24, 2014

@author: vsam
'''
from contextlib import contextmanager, ContextDecorator
from sys import exc_info
from traceback import extract_tb, format_exception_only, format_exception
from os.path import basename
import logging
import threading

######################
# Inline validation
######################


# A stack of scopes (contexts and processes)
# N.B. may need this to be thread-local

class CheckException(Exception):
    '''
    Base class for checking exceptions.
    '''
    pass
    def __init__(self, scope=None):
        self.scope = scope
    def __repr__(self):
        sc = "<%s>" % self.scope if self.scope else ""
        return "%s(%s)" % (self.__class__.__name__, sc)

class CheckFail(CheckException):
    'Raised by fail(...)'
    pass

class CheckFatal(CheckException):
    'Raised by fatal(...)'
    pass


class ScopeStack:
    '''
    A simple implementation of the scope stack. Suitable only for non-threaded
    environments. Use ThreadLocalScopeStack for more thread-local scopes.
    '''
    def __init__(self):
        self.stack = []
    def top(self):
        return self.stack[-1]
    def push(self, scope):
        pos = len(self.stack)
        self.stack.append(scope)
        scope.stack_positions.append(pos)
    def pop(self):
        scope = self.stack.pop()
        pos = scope.stack_positions.pop()
        assert pos == len(self.stack)
    def __getitem__(self, item):
        return self.stack[item]
    def __bool__(self):
        return bool(self.stack)
    def __len__(self): 
        return len(self.stack)

class ThreadLocalScopeStack(threading.local, ScopeStack):
    '''
    A thread-local scope stack
    '''
    pass


scope_stack = ThreadLocalScopeStack()


class CheckScope(ContextDecorator):
    '''
    Base class for Process and Context scopes. 

    Scopes are contextually accessed objects which implement operation
    tracing. There are two types of scopes: Process and Context. Scopes 
    are nested within one another.

    A Process scope is defined by a 'with' statement:

    with Process(name='foo', logger='bar') as p:
        <within scope 'foo'>

    The purpose of a Proccess context is to (a) encapsulate a set of operations
    and sub-scopes within it (b) provide a logger to operations within its scope.
    Typically one would have only a few Process scopes. (c) suppress the propagation
    of some exceptions.

    A Context scope is also defined by a 'with' statement:

    with Context(ipadd='127.0.0.1', current_user='vsam'):
        <within context scope (unnamed)>

    The purpose of context scopes is to (a) encapsulate a set of operations
    and sub-scopes within it (b) encapsulate scope-level information that should
    appear in messages, (c) suppress the propagation of some exceptions.

    The attributes passed at context construction are passed to the logger when
    messages are logged, via a LoggerAdapter. 

    Contexts are fine-grained and one may have many short ones.

    '''
    def __init__(self, name=None):
        '''
        Initialize scope, possibly with a name
        '''
        self.name = name       # name of the scope
        self.success = True    # record success
        self.logger_adapter = None  # the adapter to this logger, or None
        self.suppression = set()    # the set of exception classes to suppress
        self.stack_positions = []  # The positions this Scope appears in the stack

    __std_logger = None

    def suppress(self, exc_type):
        '''
        Add an expression type to the suppression list. If an expression of
        this type is caught, it will be logged and then suppressed. 

        Note that adding Exception suppresses most, but not all exceptions. Add
        BaseException to suppress everything.
        '''
        self.suppression.add(exc_type)


    @property
    def logger(self):
        '''The current logger.'''
        if hasattr(self, 'own_logger'):
            # return your own logger
            return self.own_logger
        elif self.stack_positions and self.stack_positions[-1]:
            return self.parent.logger
        else:
            return logging.getLogger()

    @property
    def log(self):
        '''A logger or adapter to use inside this scope.'''
        return self.logger_adapter if self.logger_adapter is not None else self.logger

    @property
    def parent(self):
        if self.stack_positions and self.stack_positions[0]:
            return scope_stack[self.stack_positions[0]-1]
        else:
            return None

    @property
    def process(self):
        if self.stack_positions:
            if isinstance(self, Process):
                return self
            else:
                return self.parent.process
        else:
            return None


    def __enter__(self):
        # push yourself on the stack (check that if the stack is empty then we must be
        scope_stack.push(self)
        return self

    suppress_types = ()

    def catches(self, exc_type, exc):
        '''
        Return True if the passed exception type and value should be caught at
        this scope, or propagated down the scope stack.
        '''
        return (
                (exc_type in self.suppress_types
                    and 
                    (
                        exc.scope is None or 
                        exc.scope == self.name or 
                        exc.scope is self
                    ))
            or 
                any(isinstance(exc, exct) for exct in self.suppression)
            )

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is not None:
                self.success = False
                catch = self.catches(exc_type, exc)

                if catch and exc_type not in self.suppress_types:
                    self.log.exception("An unexpected error occurred:\n%s", 
                        ''.join(format_exception(exc_type, exc, tb)))

                return catch
        finally:
            # just pop from the stack
            if self.parent: self.parent.success = self.parent.success and self.success
            assert scope_stack[-1] is self
            me = scope_stack.pop()


class Process(CheckScope):
    '''
    A process is a scope which may contain a logger for subscopes.
    The top-level scope has to be a Process.

    See the documentation of class CheckScope for details.
    '''
    suppress_types = (CheckFatal,CheckFail)

    def __init__(self, name=None, logger=None):
        super().__init__(name)
        if logger is not None:    
            if isinstance(logger, logging.Logger):
                self.logger = logger
            elif isinstance(logger, str):
                self.logger = logging.getLogger(logger)
            else: 
                assert False
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False

        self.handlers = set()

    def addScopeHandler(self, handler):
        '''
        Add a handler to the underlying logger (which may be the parent's)
        logger. This handler will be removed when the scope exits
        '''
        self.handlers.add(handler)
        if self.stack_positions:
            self.logger.addHandler(handler)

    def __enter__(self):
        super().__enter__()
        for handler in self.handlers:
            self.logger.addHandler(handler)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            for handler in self.handlers:
                self.logger.removeHandler(handler)

    @CheckScope.logger.setter
    def logger(self, logger):
        self.own_logger = logger


class Context(CheckScope):
    '''
    Contexts provide extra arguments to messages, via 
    keyword arguments given at the constructor.

    See the documentation of class CheckScope for details.
    '''
    suppress_types = (CheckFail,)

    def __init__(self, name=None, **extra):
        super().__init__(name)
        self.extra_own = extra if extra else {}

    def add(**kwargs):
        self.extra.update(kwargs)

    def __enter__(self):
        super().__enter__()

        # go down the stack and create the extras for the logger adapter
        pc = self.parent
        if pc is not None and hasattr(pc,'extra'):
            extra = dict(pc.extra)
        else:
            extra = {}

        if self.extra_own:
            extra.update(self.extra_own)
        self.extra = extra

        if extra:
            self.logger_adapter = logging.LoggerAdapter(self.logger, extra)
        return self


#
# functions
#

def _check_scope(kwargs):
    scope = kwargs['scope'] if 'scope' in kwargs else None
    return scope

def _out_of_context(msg, args, kwargs):
    "Called when fail() or fatal() are called without context"
    if 'ooc' in kwargs\
        and isinstance(kwargs['ooc'], type)\
        and issubclass(kwargs['ooc'], BaseException):
        raise kwargs['ooc'](msg, args, kwargs)
    else:
        raise RuntimeError(msg, args, kwargs)


def add_context(**kwargs):
    """
    Add context bindings to the current context (stack top).
    This method does not check for errors.
    """
    scope_stack.top().add(**kwargs)


def success():
    return scope_stack.top().success


def fail(msg=None, *args, **kwargs):
    '''
    Raise to abort this context or process, or the context named
    in the keyword argument 'scope'.
    If message evaluates to False, do not issue a message.
    All the scopes upt to the top-level process are marked as failed.

    E.g. fail('bad situation in %s', place, scope='myloc')
    '''
    if not scope_stack:
        return _out_of_context(msg, args, kwargs)
    if msg:
        scope_stack[-1].log.error(msg, *args, extra=kwargs)
    raise CheckFail(scope=_check_scope(kwargs))

def fatal(msg=None, *args, **kwargs):
    '''
    Raise to abort the nearest process, or the process named
    in the keyword argument 'scope'.
    If message evaluates to False, do not issue a message.
    All the scopes upt to the top-level process are marked as failed.

    E.g. fatal('bad situation in %s', place, scope='myloc')    
    '''
    if not scope_stack:
        return _out_of_context(msg, args, kwargs)
    if msg:
        scope_stack[-1].log.critical(msg, *args, extra=kwargs)
    raise CheckFatal(scope=_check_scope(kwargs))

def inform(msg, *args, **kwargs):
    '''
    Issue an informational message and continue.
    '''
    if not scope_stack:
        logging.getLogger().info(msg, args, extra=kwargs)
        return
    scope_stack[-1].log.info(msg, *args, extra=kwargs)
    
def warn(msg, *args, **kwargs):
    '''
    Issue a warning message and continue.
    '''
    if not scope_stack:
        logging.getLogger().warning(msg, args, extra=kwargs)
        return
    scope_stack[-1].log.warning(msg, *args, extra=kwargs)

def snafu(msg=None, *args, **kwargs):
    '''
    Issue an error message and continue. 
    If message evaluates to False, do not issue a message.
    All scopes up to the top-level are marked as failed.
    However, processing continues normally.
    '''
    if not scope_stack:
        if msg:
            logging.getLogger().error(msg, args, extra=kwargs)
        return
    if msg:
        scope_stack[-1].log.error(msg, *args, extra=kwargs)
    scope_stack[-1].success = False


#
#  Model validation
#
    
class Validation:
    """This class is used to log a model validation.
    
    In model validation, there is code that traverses the objects of the
    model and checks the validity of the data. While this is done by
    traditional functions or classes, there is need to keep a detailed account
    of the process, in order to maximize the information returned to the
    user.
    
    It is used as a context manager, and provides methods to
    output a trace of the validation to a file object.
    
    The context manager policy is to ignore all exceptions (but
    record them internally) and continue with the validation.
    
    
    Examples:
    with Validation() as V:
    
        # basic check
        V( x==1 , "check x")
        ...
        if x.failure(): V.fail("An error was detected on {0}",x)
    
        with V:
            # here we may throw, start a with block
            ...
            
        with V.section("My new section"):
            ... check stuff in a section, with indented output
            
            with V.section("My nested section"):
                ...    
    
    """
    
    INDENT_SIZE=4  # number of spaces per indent

    # detail levels
    SUCCESS=0
    INFO=10
    FAIL=20
    SECTION=30
    EXCEPTION=40
    # reserved
    QUIET=100
    
    class Abort(Exception):
        pass
    class MaxFailures(Exception):
        pass
    
    def __init__(self, outfile=None, detail=0, max_failures = 1000):
        # counters
        self.failures = 0                   # number of failures
        self.max_failures = max_failures    # max number of failures to tolerate
        self.enter = 0                      # number of calls to __enter__
        self.section_failures = []

        # output control
        self.detail = detail                # the level of detail to record
        self.level = 0                      # current indentation level
        self.outfile = outfile              # the output file
        self.exc_output_limit = 1           # number of lines per exception
    
        if self.outfile is None:
            self.detail = self.QUIET      
    
    def failure(self):
        self.failures += 1
        if self.section_failures:
            self.section_failures[-1] += 1
        if self.failures>=self.max_failures:
            raise Validation.MaxFailures
        
    def output(self, header, msg, *args, **kwargs):
        if self.outfile is None: return
        out = msg.format(*args, **kwargs)
        # split into lines
        lines = out.split('\n')
        for line in lines:
            if not line: continue
            print(" "*(self.INDENT_SIZE*self.level),
                  sep='', end='', file=self.outfile, flush=True)
            print(header, line,  
                    file=self.outfile, flush=True)
        
    def fail(self, msg, *args, **kwargs):
        self.failure()
        if msg and self.detail <= self.FAIL: 
            self.output("FAIL:", msg, *args, **kwargs)

    def exception(self, etype, evalue, etb):
        self.failure()
        if self.outfile and self.detail <= self.EXCEPTION:
            #for line in format_exception(type, value, tb, self.exc_output_limit):
            #    self.output("EXCEPTION:", line, end='')
            for frame in extract_tb(etb):
                fname, fline, func, _ = frame
                fbase = basename(fname)
                self.output("EXCEPTION:", "{0}({1}): {2}", fbase, fline, func)
            for line in format_exception_only(etype, evalue):
                self.output("EXCEPTION:", line)
    
    def success(self, msg, *args, **kwargs):
        if msg and self.detail <= self.SUCCESS: 
            self.output("SUCCESS:", msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if msg and self.detail <= self.INFO: 
            self.output("INFO:", msg, *args, **kwargs)

    def __enter__(self):
        self.enter += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Propagate Abort or MaxFailures immediately.
        # Other exceptions are swallowed

        self.enter -= 1
        if exc_type is AssertionError:
            return False
        
        if exc_type is None:
            return True

        if exc_type is Validation.Abort or self.failures>=self.max_failures:
            if self.failures==0 and self.enter==0: self.failures+=1
            return self.enter==0  # re-raise exception except if at the top-level

        try:
            if exc_type is not Validation.MaxFailures:
                self.exception(exc_type, exc_val, exc_tb)
        except Validation.MaxFailures:
            return self.enter==0 # newly raised MaxFailures
        else:
            return True # swallow other 


        
    def __call__(self, check, label=None, *args, **kwargs):
        if check:
            self.success(label, *args, **kwargs)
        else:
            self.fail(label, *args, **kwargs)
        
    @contextmanager
    def section(self, msg, *args, **kwargs):
        """Only to be called by a context manager, this starts a new section in the
        validation.
        """
        if msg and self.detail <= self.SECTION:
            self.output("SECTION:", msg, *args, **kwargs)
        self.level += 1
        self.section_failures.append(0)
        try:
            yield self
        except (AssertionError,Validation.MaxFailures,Validation.Abort):
            raise
        except Exception:
            exc_type, exc_value, exc_tb = exc_info()
            self.exception(exc_type, exc_value, exc_tb)
        finally:
            if msg and self.detail <= self.SECTION and self.section_failures[-1]>0:
                self.output("FAIL:", "Section encountered {0} failures.", self.section_failures[-1])
            self.level -= 1
            fcount = self.section_failures.pop()
            # Add subsection failures to parent
            if self.section_failures:
                self.section_failures[-1] += fcount


    def passed(self):
        return self.failures==0
    def passed_section(self):
        if self.section_failures:
            return self.section_failures[-1]==0
        return True


