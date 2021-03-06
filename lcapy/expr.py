"""This file provides the Expr class.  This attempts to create a
consistent interface to SymPy's expressions.

Copyright 2014--2019 Michael Hayes, UCECE

"""


# TODO, propagate assumptions for arithmetic.........  This may be
# tricky.  At the moment only a limited propagation of assumptions are
# performed.

from __future__ import division
from .ratfun import Ratfun
from .sym import sympify, symsimplify, j, omegasym, symdebug
from .sym import capitalize_name, tsym, symsymbol, symbol_map
from .state import state
from .printing import pprint, pretty, print_str, latex
from .functions import sqrt, log10, atan2, gcd, exp, Function
import numpy as np
import sympy as sym
from sympy.utilities.lambdify import lambdify
from .sym import simplify
from collections import OrderedDict

class ExprPrint(object):

    @property
    def _pexpr(self):
        """Return expression for printing."""
        
        if hasattr(self, 'expr'):
            return self.expr
        return self
    
    def __repr__(self):
        """This is called by repr(expr).  It is used, e.g., when printing
        in the debugger."""
        
        return '%s(%s)' % (self.__class__.__name__, print_str(self._pexpr))

    def _repr_pretty_(self, p, cycle):
        """This is used by jupyter notebooks to display an expression using
        unicode.  It is also called by IPython when displaying an
        expression.""" 

        p.text(pretty(self._pexpr))

    # Note, _repr_latex_ is handled at the end of this file.
        
    def pretty(self):
        """Make pretty string."""
        return pretty(self._pexpr)

    def prettyans(self, name):
        """Make pretty string with LHS name."""
        return pretty(sym.Eq(sympify(name), self._pexpr))

    def pprint(self):
        """Pretty print"""
        pprint(self._pexpr)

    def pprintans(self, name):
        """Pretty print string with LHS name."""
        print(self.prettyans(name))

    def latex(self, **kwargs):
        """Make latex string."""
        return latex(self, **kwargs)

    def latex_math(self, **kwargs):
        """Make latex math-mode string."""
        return '$' + self.latex(**kwargs) + '$'

    def latexans(self, name, **kwargs):
        """Print latex string with LHS name."""
        return latex(sym.Eq(sympify(name), self._pexpr), **kwargs)


class ExprContainer(object):    

    def evaluate(self):
        
        """Evaluate each element to convert to floating point."""        
        return self.__class__([v.evalf() for v in self])
    
    def simplify(self):
        """Simplify each element."""
        
        return self.__class__([simplify(v) for v in self])

    @property    
    def symbols(self):
        """Return dictionary of symbols in the expression keyed by name."""
        
        symbols = {}
        for expr in list(self):
            symbols.update(expr.symbols)
        return symbols

    
class ExprMisc(object):

    @property    
    def pdb(self):
        """Enter the python debugger."""
        
        import pdb; pdb.set_trace()
        return self

    def debug(self):

        name = self.__class__.__name__
        s = '%s(' % name
        print(symdebug(self.expr, s , len(name) + 1))

    
class ExprDict(ExprPrint, ExprContainer, ExprMisc, OrderedDict):

    """Decorator class for dictionary created by sympy."""

    def evaluate(self):
        """Evaluate each element to convert to floating point.
        The keys are also converted if possible to handle
        dictionaries of poles/zeros."""

        new = self.__class__()
        for k, v in self.items():
            try:
                k = k.evalf()
            except:
                pass
            try:
                v = v.evalf()
            except:
                pass            
                
            new[k] = v
        return new

    def simplify(self):
        """Simplify each element but not the keys."""

        new = self.__class__()
        for k, v in self.items():
            new[k] = simplify(v)
        return new

    
class ExprList(ExprPrint, list, ExprContainer, ExprMisc):
    """Decorator class for list created by sympy."""

    # Have ExprPrint first so that its _repr__pretty_ is called
    # in preference to list's one.  Alternatively, add explicit
    # _repr_pretty_ method here.
    
    def __init__(self, arglist):
        eargs = [expr(e) for e in arglist]
        super (ExprList, self).__init__(eargs)

    def subs(self, *args, **kwargs):
        """Substitute variables in expression, see sympy.subs for usage."""
        
        return expr([e.subs(*args, **kwargs) for e in self])
        
    
class ExprTuple(ExprPrint, tuple, ExprContainer, ExprMisc):
    """Decorator class for tuple created by sympy."""

    def __init__(self, arglist):
        eargs = [expr(e) for e in arglist]
        super (ExprTuple, self).__init__(tuple(eargs))

    def subs(self, *args, **kwargs):
        """Substitute variables in expression, see sympy.subs for usage."""
        
        return expr((e.subs(*args, **kwargs) for e in self))

    
class Expr(ExprPrint, ExprMisc):
    """Decorator class for sympy classes derived from sympy.Expr"""

    one_sided = False
    var = None

    # Perhaps have lookup table for operands to determine
    # the resultant type?  For example, Vs / Vs -> Hs
    # Vs / Is -> Zs,  Is * Zs -> Vs
    # But what about Vs**2 ?

    @property
    def _pexpr(self):
        """Return expression for printing."""
        return self.expr

    def __init__(self, arg, **assumptions):
        """

         There are two types of assumptions:
           1. The sympy assumptions associated with symbols, for example,
              real=True.
           2. The expr assumptions such as dc, ac, causal.  These
              are primarily to help the inverse Laplace transform for sExpr
              classes.  The omega assumption is required for Phasors."""

        if isinstance(arg, Expr):
            if assumptions == {}:
                assumptions = arg.assumptions.copy()
            self.assumptions = assumptions.copy()
            self.expr = arg.expr
            return
            
        # Perhaps could set dc?
        if arg == 0:
            assumptions['causal'] = True

        self.assumptions = assumptions.copy()
        # Remove Lcapy assumptions from SymPy expr.
        assumptions.pop('nid', None)
        assumptions.pop('ac', None)
        assumptions.pop('dc', None)
        assumptions.pop('causal', None)                        
        
        self.expr = sympify(arg, **assumptions)

    def __str__(self, printer=None):
        """String representation of expression."""
        return print_str(self._pexpr)

    def __repr__(self):
        """This is called by repr(expr).  It is used, e.g., when printing
        in the debugger."""
        
        return '%s(%s)' % (self.__class__.__name__, print_str(self._pexpr))

    def _repr_pretty_(self, p, cycle):
        """This is used by jupyter notebooks to display an expression using
        unicode.  It is also called by IPython when displaying an
        expression.""" 

        p.text(pretty(self._pexpr))

    def _repr_latex_(self):
        """This is used by jupyter notebooks to display an expression using
        LaTeX markup.  However, this requires mathjax.  If this method
        is not defined, jupyter falls back on _repr_pretty_ which
        outputs unicode."""

        # This is called for Expr but not ExprList
        return '$$' + latex(self._pexpr) + '$$'        

    def _latex(self, *args, **kwargs):
        """Make latex string.  This is called by sympy.latex when it
        encounters an Expr type."""

        # This works in conjunction with LatexPrinter._print
        # It is a hack to allow printing of _Matrix types
        # and its elements.
        # This also catches sym.latex(expr) where expr is
        # an Lcapy expr.

        return self.latex(**kwargs)

    def _pretty(self, *args, **kwargs):
        """Make pretty string."""

        # This works in conjunction with Printer._print
        # It is a hack to allow printing of _Matrix types
        # and its elements.
        expr = self._pexpr
        printer = args[0]

        return printer._print(expr)

    @property
    def causal(self):
        return self.is_causal
        
    @causal.setter
    def causal(self, value):
        self.assumptions['causal'] = value
        if value:
            self.assumptions['dc'] = False
            self.assumptions['ac'] = False
        
    def infer_assumptions(self):
        self.assumptions['dc'] = None
        self.assumptions['ac'] = None
        self.assumptions['causal'] = None

    @property
    def is_dc(self):
        if 'dc' not in self.assumptions:
            self.infer_assumptions()
        return self.assumptions['dc'] == True

    @property
    def is_ac(self):
        if 'ac' not in self.assumptions:
            self.infer_assumptions()
        return self.assumptions['ac'] == True

    @property
    def is_causal(self):
        if 'causal' not in self.assumptions:
            self.infer_assumptions()
        return self.assumptions['causal'] == True

    @property
    def is_complex(self):
        if 'complex' not in self.assumptions:
            return False
        return self.assumptions['complex'] == True

    @property
    def val(self):
        """Return floating point value of expression if it can be evaluated,
        otherwise the expression."""

        return self.evalf()

    @property
    def evalf(self):
        """Return floating point value of expression if it can be evaluated,
        otherwise the expression."""

        return self.expr.evalf()    

    @property
    def omega(self):
        """Return angular frequency."""

        if 'omega' not in self.assumptions:
            return omegasym
        return self.assumptions['omega']

    def __hash__(self):
        # This is needed for Python3 so can create a dict key,
        # say for subs.
        return hash(self.expr)

# This will allow sym.sympify to magically extract the sympy expression
# but it will also bypass our __rmul__, __radd__, etc. methods that get called
# when sympy punts.  Thus pi * t becomes a Mul rather than tExpr.
#
#    def _sympy_(self):
#        # This is called from sym.sympify
#        return self.expr

    def __getattr__(self, attr):

        if False:
            print(self.__class__.__name__, attr)
        
        # This gets called if there is no explicit attribute attr for
        # this instance.  We call the method of the wrapped sympy
        # class and rewrap the returned value if it is a sympy Expr
        # object.

        # FIXME.  This propagates the assumptions.  There is a
        # possibility that the operation may violate them.
        expr = self.expr
        if hasattr(expr, attr):
            a = getattr(expr, attr)

            # If it is not callable, directly wrap it.
            if not hasattr(a, '__call__'):
                if not isinstance(a, sym.Expr):
                    return a
                ret = a()                
                if hasattr(self, 'assumptions'):
                    return self.__class__(ret, **self.assumptions)
                return self.__class__(ret)

            # If it is callable, create a function to pass arguments
            # through and wrap its return value.
            def wrap(*args):
                """This is wrapper for a SymPy function.
                For help, see the SymPy documentation."""

                ret = a(*args)

                if not isinstance(ret, sym.Expr):
                    return ret

                # Wrap the return value
                cls = self.__class__
                if hasattr(self, 'assumptions'):
                    return cls(ret, **self.assumptions)
                return cls(ret)

            return wrap

        # Try looking for a sympy function with the same name,
        # such as sqrt, log, etc.
        # On second thoughts, this may confuse the user since
        # we will pick up methods such as laplace_transform.
        # Perhaps should have a list of allowable functions?
        if True or not hasattr(sym, attr):
            raise AttributeError(
                "%s has no attribute %s." % (self.__class__.__name__, attr))

        def wrap1(*args):

            ret = getattr(sym, attr)(expr, *args)
            if not isinstance(ret, sym.Expr):
                return ret

            # Wrap the return value
            return self.__class__(ret)

        return wrap1

    def __abs__(self):
        """Absolute value."""

        return self.__class__(self.abs, **self.assumptions)

    def __neg__(self):
        """Negation."""

        return self.__class__(-self.expr, **self.assumptions)

    def __compat_mul__(self, x, op):
        """Check if args are compatible and if so return compatible class."""

        # Could also convert Vs / Zs -> Is, etc.
        # But, what about (Vs * Vs) / (Vs * Is) ???

        assumptions = {}
        
        cls = self.__class__
        if not isinstance(x, Expr):
            return cls, self, cls(x), assumptions

        xcls = x.__class__

        if isinstance(self, sExpr) and isinstance(x, sExpr):
            if self.is_causal or x.is_causal:
                assumptions = {'causal' : True}
            elif self.is_dc and x.is_dc:
                assumptions = self.assumptions
            elif self.is_ac and x.is_ac:
                assumptions = self.assumptions
            elif self.is_ac and x.is_dc:
                assumptions = {'ac' : True}
            elif self.is_dc and x.is_ac:
                assumptions = {'ac' : True}                

        if cls == xcls:
            return cls, self, cls(x), assumptions

        # Allow omega * t but treat as t expression.
        if isinstance(self, omegaExpr) and isinstance(x, tExpr):
            return xcls, self, x, assumptions
        if isinstance(self, tExpr) and isinstance(x, omegaExpr):
            return cls, self, x, assumptions                    
        
        if xcls in (Expr, cExpr):
            return cls, self, cls(x), assumptions

        if cls in (Expr, cExpr):
            return xcls, self, x, assumptions

        if isinstance(x, cls):
            return xcls, self, cls(x), assumptions

        if isinstance(self, xcls):
            return cls, self, cls(x), assumptions

        if isinstance(self, tExpr) and isinstance(x, tExpr):
            return cls, self, cls(x), assumptions

        if isinstance(self, sExpr) and isinstance(x, sExpr):
            return cls, self, cls(x), assumptions

        if isinstance(self, omegaExpr) and isinstance(x, omegaExpr):
            return cls, self, cls(x), assumptions

        raise ValueError('Cannot combine %s(%s) with %s(%s) for %s' %
                         (cls.__name__, self, xcls.__name__, x, op))

    def __compat_add__(self, x, op):

        # Disallow Vs + Is, etc.

        assumptions = {}

        cls = self.__class__
        if not isinstance(x, Expr):
            return cls, self, cls(x), assumptions

        xcls = x.__class__

        if isinstance(self, sExpr) and isinstance(x, sExpr):
            if self.assumptions == x.assumptions:
                assumptions = self.assumptions
        
        if cls == xcls:
            return cls, self, x, assumptions

        # Handle Vs + sExpr etc.
        if isinstance(self, xcls):
            return cls, self, x, assumptions

        # Handle sExpr + Vs etc.
        if isinstance(x, cls):
            return xcls, self, cls(x), assumptions

        if xcls in (Expr, cExpr):
            return cls, self, x, assumptions

        if cls in (Expr, cExpr):
            return xcls, cls(self), x, assumptions

        if cls in (Impedance, Admittance) and isinstance(x, omegaExpr):
            return cls, self, cls(x), assumptions        

        raise ValueError('Cannot combine %s(%s) with %s(%s) for %s' %
                         (cls.__name__, self, xcls.__name__, x, op))

    def __rdiv__(self, x):
        """Reverse divide"""

        cls, self, x, assumptions = self.__compat_mul__(x, '/')
        return cls(x.expr / self.expr, **assumptions)

    def __rtruediv__(self, x):
        """Reverse true divide"""

        cls, self, x, assumptions = self.__compat_mul__(x, '/')
        return cls(x.expr / self.expr, **assumptions)

    def __mul__(self, x):
        """Multiply"""
        from .super import Super

        if isinstance(x, Super):
            return x.__mul__(self)

        cls, self, x, assumptions = self.__compat_mul__(x, '*')
        return cls(self.expr * x.expr, **assumptions)

    def __rmul__(self, x):
        """Reverse multiply"""

        cls, self, x, assumptions = self.__compat_mul__(x, '*')
        return cls(self.expr * x.expr, **assumptions)

    def __div__(self, x):
        """Divide"""

        cls, self, x, assumptions = self.__compat_mul__(x, '/')
        return cls(self.expr / x.expr, **assumptions)

    def __truediv__(self, x):
        """True divide"""

        cls, self, x, assumptions = self.__compat_mul__(x, '/')
        return cls(self.expr / x.expr, **assumptions)

    def __add__(self, x):
        """Add"""

        cls, self, x, assumptions = self.__compat_add__(x, '+')
        return cls(self.expr + x.expr, **assumptions)

    def __radd__(self, x):
        """Reverse add"""

        cls, self, x, assumptions = self.__compat_add__(x, '+')
        return cls(self.expr + x.expr, **assumptions)

    def __rsub__(self, x):
        """Reverse subtract"""

        cls, self, x, assumptions = self.__compat_add__(x, '-')
        return cls(x.expr - self.expr, **assumptions)

    def __sub__(self, x):
        """Subtract"""

        cls, self, x, assumptions = self.__compat_add__(x, '-')
        return cls(self.expr - x.expr, **assumptions)

    def __pow__(self, x):
        """Pow"""

        # TODO: FIXME
        cls, self, x, assumptions = self.__compat_mul__(x, '**')
        return cls(self.expr ** x.expr, **assumptions)

    def __or__(self, x):
        """Parallel combination"""

        return self.parallel(x)

    def __eq__(self, x):
        """Test for mathematical equality as far as possible.
        This cannot be guaranteed since it depends on simplification.
        Note, SymPy comparison is for structural equality.

        Note t == 't' since the second operand gets converted to the
        type of the first operand."""

        # Note, this is used by the in operator.

        if x is None:
            return False

        try:
            cls, self, x, assumptions = self.__compat_add__(x, '==')
        except ValueError:
            return False
            
        x = cls(x)

        # This fails if one of the operands has the is_real attribute
        # and the other doesn't...
        return sym.simplify(self.expr - x.expr) == 0

    def __ne__(self, x):
        """Test for mathematical inequality as far as possible.
        This cannot be guaranteed since it depends on simplification.
        Note, SymPy comparison is for structural equality."""

        if x is None:
            return True

        cls, self, x, assumptions = self.__compat_add__(x, '!=')
        x = cls(x)

        return sym.simplify(self.expr - x.expr) != 0        

    def __gt__(self, x):
        """Greater than"""

        if x is None:
            return True

        cls, self, x, assumptions = self.__compat_add__(x, '>')
        x = cls(x)

        return self.expr > x.expr

    def __ge__(self, x):
        """Greater than or equal"""

        if x is None:
            return True

        cls, self, x, assumptions = self.__compat_add__(x, '>=')
        x = cls(x)

        return self.expr >= x.expr

    def __lt__(self, x):
        """Less than"""

        if x is None:
            return True

        cls, self, x, assumptions = self.__compat_add__(x, '<')
        x = cls(x)

        return self.expr < x.expr

    def __le__(self, x):
        """Less than or equal"""

        if x is None:
            return True

        cls, self, x, assumptions = self.__compat_add__(x, '<=')
        x = cls(x)

        return self.expr <= x.expr

    def parallel(self, x):
        """Parallel combination"""

        cls, self, x, assumptions = self.__compat_add__(x, '|')
        x = cls(x)

        return cls(self.expr * x.expr / (self.expr + x.expr), **assumptions)

    @property
    def conjugate(self):
        """Return complex conjugate."""

        return self.__class__(sym.conjugate(self.expr), **self.assumptions)

    @property
    def real(self):
        """Return real part."""

        assumptions = self.assumptions.copy()
        assumptions['real'] = True        

        dst = self.__class__(symsimplify(sym.re(self.expr)), **assumptions)
        dst.part = 'real'
        return dst

    @property
    def imag(self):
        """Return imaginary part."""

        assumptions = self.assumptions.copy()
        assumptions['real'] = True
        
        dst = self.__class__(symsimplify(sym.im(self.expr)), **assumptions)
        dst.part = 'imaginary'
        return dst

    @property
    def real_imag(self):
        """Rewrite as x + j * y"""

        return self.real + j * self.imag

    @property
    def _ratfun(self):
        return Ratfun(self.expr, self.var)

    @property
    def K(self):
        """Return gain."""

        return self.N.coeffs()[0] / self.D.coeffs()[0] 
    
    @property
    def N(self):
        """Return numerator of rational function."""

        return self.numerator

    @property
    def D(self):
        """Return denominator of rational function."""

        if self.var is None:
            return self.__class__(1)
        
        return self.denominator

    @property
    def numerator(self):
        """Return numerator of rational function."""

        if self.var is None:
            return self

        return self.__class__(self._ratfun.numerator)

    @property
    def denominator(self):
        """Return denominator of rational function."""

        return self.__class__(self._ratfun.denominator)

    def rationalize_denominator(self):
        """Rationalize denominator by multiplying numerator and denominator by
        complex conjugate of denominator."""

        N = self.N
        D = self.D
        Dconj = D.conjugate
        Nnew = (N * Dconj).simplify()
        #Dnew = (D * Dconj).simplify()
        Dnew = (D.real**2 + D.imag**2).simplify()

        Nnew = Nnew.real_imag

        return Nnew / Dnew

    def divide_top_and_bottom(self, factor):
        """Divide numerator and denominator by common factor."""

        N = (self.N / factor).expand()
        D = (self.D / factor).expand()

        return N / D
    
    @property
    def magnitude(self):
        """Return magnitude"""

        if self.is_real:
            dst = self
        else:
            R = self.rationalize_denominator()
            N = R.N
            Dnew = R.D
            Nnew = sqrt((N.real**2 + N.imag**2).simplify())
            dst = Nnew / Dnew

        dst.part = 'magnitude'
        return dst

    @property
    def abs(self):
        """Return magnitude"""

        return self.magnitude

    @property
    def sign(self):
        """Return sign"""

        return self.__class__(sym.sign(self.expr))

    @property
    def dB(self):
        """Return magnitude in dB."""

        # Need to clip for a desired dynamic range?
        # Assume reference is 1.
        dst = 20 * log10(self.magnitude)
        dst.part = 'magnitude'
        dst.units = 'dB'
        return dst

    @property
    def phase(self):
        """Return phase in radians."""

        R = self.rationalize_denominator()
        N = R.N

        if N.imag == 0:
            dst = N.imag
        else:
            if N.real != 0:
                G = gcd(N.real, N.imag)
                N = N / G
            dst = atan2(N.imag, N.real)
            
        dst.part = 'phase'
        dst.units = 'rad'
        return dst

    @property
    def phase_degrees(self):
        """Return phase in degrees."""

        dst = self.phase * 180.0 / sym.pi
        dst.part = 'phase'
        dst.units = 'degrees'
        return dst

    @property
    def angle(self):
        """Return phase angle"""

        return self.phase

    @property
    def polar(self):
        """Return in polar format"""

        return self.abs * exp(j * self.phase)

    @property
    def cartesian(self):
        """Return in Cartesian format"""

        return self.real + j * self.imag
    
    @property
    def is_number(self):

        return self.expr.is_number

    @property
    def is_constant(self):

        expr = self.expr

        # Workaround for sympy bug
        # a = sym.sympify('DiracDelta(t)')
        # a.is_constant()
        
        if expr.has(sym.DiracDelta):
            return False
        
        return expr.is_constant()

    def evaluate(self, arg=None):
        """Evaluate expression at arg.  arg may be a scalar, or a vector.
        The result is of type float or complex.

        There can be only one or fewer undefined variables in the expression.
        This is replaced by arg and then evaluated to obtain a result.
        """

        def evaluate_expr(expr, var, arg):

            # For some reason the new lambdify will convert a float
            # argument to complex
            
            def exp(arg):

                # Hack to handle exp(-a * t) * Heaviside(t) for t < 0
                # by trying to avoid inf when number overflows float.

                if isinstance(arg, complex):
                    if arg.real > 500:
                        arg = 500 + 1j * arg.imag
                elif arg > 500:
                    arg = 500;                        

                return np.exp(arg)

            def dirac(arg):
                return np.inf if arg == 0.0 else 0.0

            def heaviside(arg):
                return 1.0 if arg >= 0.0 else 0.0

            def sqrt(arg):
                # Large numbers get converted to ints and int has no sqrt
                # attribute so convert to float.
                if isinstance(arg, int):
                    arg = float(arg)
                if not isinstance(arg, complex) and arg < 0:
                    arg = arg + 0j
                return np.sqrt(arg)

            try:
                arg0 = arg[0]
                scalar = False
            except:
                arg0 = arg
                scalar = True

            # For negative arguments, np.sqrt will return Nan.
            # np.lib.scimath.sqrt converts to complex but cannot be used
            # for lamdification!
            func = lambdify(var, expr,
                            ({'DiracDelta' : dirac,
                              'Heaviside' : heaviside,
                              'sqrt' : sqrt, 'exp' : exp},
                             "scipy", "numpy", "math", "sympy"))

            try:
                result = func(arg0)
                response = complex(result)
            except NameError as e:
                raise RuntimeError('Cannot evaluate expression %s: %s' % (self, e))
            except AttributeError as e:
                if False and expr.is_Piecewise:
                    raise RuntimeError(
                        'Cannot evaluate expression %s,'
                        ' due to undetermined conditional result' % self)

                raise RuntimeError(
                    'Cannot evaluate expression %s,'
                    ' probably have a mysterious function: %s' % (self, e))

            except TypeError as e:
                raise RuntimeError('Cannot evaluate expression %s: %s' % (self, e))
            
            if scalar:
                if np.allclose(response.imag, 0.0):
                    response = response.real
                return response

            try:
                response = np.array([complex(func(arg0)) for arg0 in arg])
            except TypeError:
                raise TypeError(
                    'Cannot evaluate expression %s,'
                    ' probably have undefined symbols' % self)

            if np.allclose(response.imag, 0.0):
                response = response.real
            return response

        expr = self.expr

        if not hasattr(self, 'var') or self.var is None:
            symbols = list(expr.free_symbols)
            if arg is None:
                if len(symbols) == 0:
                    return expr.evalf()                    
                raise ValueError('Undefined symbols %s in expression %s' % (tuple(symbols), self))                                    
            if len(symbols) == 0:
                print('Ignoring arg %s' % arg)
                return expr.evalf()                
            elif len(symbols) == 1:            
                return evaluate_expr(expr, symbols[0], arg)
            else:
                raise ValueError('Undefined symbols %s in expression %s' % (tuple(symbols), self))                
                
            
        var = self.var
        # Use symbol names to avoid problems with symbols of the same
        # name with different assumptions.
        varname = var.name
        free_symbols = set([symbol.name for symbol in expr.free_symbols])
        if varname in free_symbols:
            free_symbols -= set((varname, ))
            if free_symbols != set():
                raise ValueError('Undefined symbols %s in expression %s' % (tuple(free_symbols), self))

        if arg is None:
            if expr.find(var) != set():
                raise ValueError('Need value to evaluate expression at')
            # The arg is irrelevant since the expression is a constant.
            arg = 0

        try:
            arg = arg.evalf()
        except:
            pass

        return evaluate_expr(expr, var, arg)

    def has(self, subexpr):
        """Test whether the sub-expression is contained.  For example,
         V.has(exp(t)) 
         V.has(t)

        """

        if isinstance(subexpr, (Expr, Function)):
            subexpr = subexpr.expr
        return self.expr.has(subexpr)

    def has_symbol(self, sym):
        """Test if have symbol contained.  For example,
        V.has_symbol('a')
        V.has_symbol(t)
        
        """                        
        return self.has(symbol(sym))
    
    def _subs1(self, old, new, **kwargs):

        # This will fail if a variable has different attributes,
        # such as positive or real.
        # Should check for bogus substitutions, such as t for s.

        if new is old:
            return self

        expr = new
        if isinstance(new, Expr):
            if old == self.var:
                cls = new.__class__
            else:
                cls = self.__class__                
            expr = new.expr
        else:
            cls = self.__class__
            expr = sympify(expr)

        class_map = {(Hs, omegaExpr) : Homega,
                     (Is, omegaExpr) : Iomega,
                     (Vs, omegaExpr) : Vomega,
                     (Ys, omegaExpr) : Yomega,
                     (Zs, omegaExpr) : Zomega,
                     (Admittance, omegaExpr) : Yomega,
                     (Impedance, omegaExpr) : Zomega,                     
                     (Hs, fExpr) : Hf,
                     (Is, fExpr) : If,
                     (Vs, fExpr) : Vf,
                     (Ys, fExpr) : Yf,
                     (Zs, fExpr) : Zf,
                     (Admittance, fExpr) : Yf,
                     (Impedance, fExpr) : Zf,                     
                     (Hf, omegaExpr) : Homega,
                     (If, omegaExpr) : Iomega,
                     (Vf, omegaExpr) : Vomega,
                     (Yf, omegaExpr) : Yomega,
                     (Zf, omegaExpr) : Zomega,
                     (Homega, fExpr) : Hf,
                     (Iomega, fExpr) : If,
                     (Vomega, fExpr) : Vf,
                     (Yomega, fExpr) : Yf,
                     (Zomega, fExpr) : Zf,
                     (Admittance, sExpr) : Ys,
                     (Impedance, sExpr) : Zs}                     

        if (self.__class__, new.__class__) in class_map:
            cls = class_map[(self.__class__, new.__class__)]

        old = symbol_map(old)
        result = self.expr.subs(old, expr)

        # If get empty Piecewise, then result unknowable.  TODO: sympy
        # 1.2 requires Piecewise constructor to have at least one
        # pair.
        if False and result.is_Piecewise and result == sym.Piecewise():
            result = sym.nan

        return cls(result, **self.assumptions)

    def transform(self, arg, **assumptions):
        """Transform into a different domain."""
        
        from .transform import transform
        return transform(self, arg, **assumptions)

    def __call__(self, arg, **assumptions):
        """Substitute arg for variable.  If arg is an tuple or list
        return a list.  If arg is an numpy array, return
        numpy array.

        See also evaluate.
        """

        if isinstance(arg, (tuple, list)):
            return [self._subs1(self.var, arg1) for arg1 in arg]

        if isinstance(arg, np.ndarray):
            return np.array([self._subs1(self.var, arg1) for arg1 in arg])

        from .transform import call        
        return call(self, arg, **assumptions)

    def limit(self, var, value, dir='+'):
        """Determine limit of expression(var) at var = value."""

        # Need to use lcapy sympify otherwise could use
        # getattr to call sym.limit.

        var = sympify(var)
        value = sympify(value)

        # Experimental.  Compare symbols by names.
        symbols = list(self.expr.free_symbols)
        symbolnames = [str(symbol) for symbol in symbols]
        if str(var) not in symbolnames:
            return self
        var = symbols[symbolnames.index(str(var))]
        
        ret = sym.limit(self.expr, var, value)
        if hasattr(self, 'assumptions'):
            return self.__class__(ret, **self.assumptions)
        return self.__class__(ret)

    def simplify(self):
        """Simplify expression."""
        
        ret = symsimplify(self.expr)
        return self.__class__(ret, **self.assumptions)

    def subs(self, *args, **kwargs):
        """Substitute variables in expression, see sympy.subs for usage."""

        if len(args) > 2:
            raise ValueError('Too many arguments')
        if len(args) == 0:
            raise ValueError('No arguments')

        if len(args) == 2:
            return self._subs1(args[0], args[1])

        if  isinstance(args[0], dict):
            dst = self
            for key, val in args[0].items():
                dst = dst._subs1(key, val, **kwargs)

            return dst

        return self._subs1(self.var, args[0])

    @property
    def label(self):

        label = ''
        if hasattr(self, 'quantity'):
            label += self.quantity
            if hasattr(self, 'part'):
                label += ' ' + self.part
        else:
            if hasattr(self, 'part'):
                label += capitalize_name(self.part)
        if hasattr(self, 'units') and self.units != '':
            label += ' (%s)' % self.units
        return label

    @property
    def domain_label(self):

        label = ''
        if hasattr(self, 'domain_name'):
            label += '%s' % self.domain_name
        if hasattr(self, 'domain_units'):
            label += ' (%s)' % self.domain_units
        return label

    def differentiate(self, arg=None):

        if arg is None:
            arg = self.var
        arg = self._tweak_arg(arg)
            
        return self.__class__(sym.diff(self.expr, arg))

    def diff(self, arg=None):

        return self.differentiate(arg)

    def _tweak_arg(self, arg):

        if isinstance(arg, Expr):
            return arg.expr

        if isinstance(arg, tuple):
            return tuple([self._tweak_arg(arg1) for arg1 in arg])

        if isinstance(arg, list):
            return [self._tweak_arg(arg1) for arg1 in arg]

        return arg

    def integrate(self, arg=None, **kwargs):

        if arg is None:
            arg = self.var

        arg = self._tweak_arg(arg)
        return self.__class__(sym.integrate(self.expr, arg, **kwargs))

    def solve(self, *symbols, **flags):

        symbols = [symbol_map(symbol) for symbol in symbols]
        return expr(sym.solve(self.expr, *symbols, **flags))

    @property
    def symbols(self):
        """Return dictionary of symbols in the expression keyed by name."""
        symdict = {sym.name:sym for sym in self.free_symbols}

        # Look for V(s), etc.
        funcdict = {atom.func.__name__:atom for atom in self.atoms(sym.function.AppliedUndef)}        

        symdict.update(funcdict)
        return symdict

    def roots(self, aslist=False):
        """Return roots of expression as a dictionary
        Note this may not find them all."""

        roots = self._ratfun.roots()
        if not aslist:
            return expr(roots)
        rootslist = []
        for root, count in roots.items():
            rootslist += [root] * count
        return expr(rootslist)
            
    def zeros(self, aslist=False):
        """Return zeroes of expression as a dictionary
        Note this may not find them all."""

        return self.N.roots(aslist)

    def poles(self, aslist=False, damping=None):
        """Return poles of expression as a dictionary
        Note this may not find them all."""

        poles = self._ratfun.poles(damping=damping)
        
        if not aslist:
            polesdict = {}
            for pole in poles:
                key = pole.expr
                if key in polesdict:
                    polesdict[pole.expr] += pole.n
                else:
                    polesdict[pole.expr] = pole.n
            return expr(polesdict)
            
        poleslist = []
        for pole in poles:
            poleslist += [pole.expr] * pole.n
        return expr(poleslist)

    def canonical(self, factor_const=False):
        """Convert rational function to canonical form (aka polynomial form);
        this is like general form but with a unity highest power of
        denominator.  For example,

        (5 * s**2 + 5 * s + 5) / (s**2 + 4)

        If factor_const is True, factor constants from numerator, for example,

        5 * (s**2 + s + 1) / (s**2 + 4)

        This is also called gain-polynomial form.

        See also general, partfrac, standard, timeconst, and ZPK

        """

        return self.__class__(self._ratfun.canonical(factor_const), **self.assumptions)

    def general(self):
        """Convert rational function to general form.  For example,

        (5 * s**2 + 10 * s + 5) / (s**2 + 4)

        See also canonical, partfrac, standard, timeconst, and ZPK."""

        return self.__class__(self._ratfun.general(), **self.assumptions)

    def partfrac(self, combine_conjugates=False, damping=None):
        """Convert rational function into partial fraction form.   For example,

        5 + (5 - 15 * j / 4) / (s + 2 * j) + (5 + 15 * j / 4) / (s - 2 * j)

        If combine_conjugates is True then the pair of partial
        fractions for complex conjugate poles are combined.

        See also canonical, standard, general, timeconst, and ZPK."""

        return self.__class__(self._ratfun.partfrac(combine_conjugates,
                                                    damping),
                              **self.assumptions)

    def standard(self):
        """Convert rational function into mixed fraction form.  For example,

        (5 * s - 5) / (s**2 + 4) + 5

        This is the sum of strictly proper rational function and a
        polynomial.

        See also canonical, general, partfrac, timeconst, and ZPK.

        """

        return self.__class__(self._ratfun.standard(), **self.assumptions)

    def mixedfrac(self):
        """This is an alias for standard and my be deprecated."""
        
        return self.standard()

    def timeconst(self):
        """Convert rational function into time constant form.  For example,

        5 * (s**2 + 2 * s + 1) / (4 * (s**2 / 4 + 1))

        See also canonical, general, standard, partfrac and ZPK."""

        return self.__class__(self._ratfun.timeconst(), **self.assumptions)

    def ZPK(self):
        """Convert to zero-pole-gain (ZPK) form (factored form).  For example,

        5 * (s + 1)**2 / ((s - 2 * j) * (s + 2 * j))

        See also canonical, general, standard, partfrac, and timeconst.

        """

        return self.__class__(self._ratfun.ZPK(), **self.assumptions)

    def factored(self):
        """Convert to factored form.  For example,

        5 * (s + 1)**2 / ((s - 2 * j) * (s + 2 * j))

        This is an alias for ZPK.  See also canonical, general,
        standard, partfrac, and timeconst.

        """

        return self.__class__(self._ratfun.ZPK(), **self.assumptions)
    
    def expandcanonical(self):
        """Expand in terms for different powers with each term
        expressed in canonical form.  For example,

        s / (s**2 + 4) + 5 / (s**2 + 4)

        See also canonical, general, partfrac, timeconst, and ZPK."""

        return self.__class__(self._ratfun.expandcanonical(), **self.assumptions)

    def coeffs(self, norm=False):
        """Return list of coeffs assuming the expr is a polynomial in s.  The
        highest powers come first.  This will fail for a rational function.
        Instead use expr.N.coeffs or expr.D.coeffs for numerator
        or denominator respectively.
        
        If norm is True, normalise coefficients to highest power is 1."""

        try:
            z = sym.Poly(self.expr, self.var)
        except:
            raise ValueError('Use .N or .D attribute to specify numerator or denominator of rational function')

        c = z.all_coeffs()
        if norm:
            return expr([sym.simplify(c1 / c[0]) for c1 in c])
            
        return expr(c)

    def normcoeffs(self):
        """Return list of coeffs (normalised so the highest power is 1)
        assuming the expr is a polynomial in s.  The highest powers
        come first.  This will fail for a rational function.  Instead
        use expr.N.normcoeffs or expr.D.normcoeffs for numerator or
        denominator respectively."""

        return self.coeffs(norm=True)

    @property
    def degree(self):
        """Return the degree (order) of the rational function.

        This the maximum of the numerator and denominator degrees.
        Note zero has a degree of -inf."""
        
        return self._ratfun.degree

    @property
    def Ndegree(self):
        """Return the degree (order) of the numerator of a rational function.
        This will throw an exception if the expression is not a
        rational function.

        Note zero has a degree of -inf.

        """
        
        return self._ratfun.Ndegree

    @property
    def Ddegree(self):
        """Return the degree (order) of the denominator of a rational function.
        This will throw an exception if the expression is not a
        rational function.

        Note zero has a degree of -inf."""
        
        return self._ratfun.Ddegree

    @property
    def strictly_proper(self):
        """Return True if the degree of the dominator is greater
        than the degree of the numerator.
        This will throw an exception if the expression is not a
        rational function."""

        return self._ratfun.strictly_proper
    
    def prune_HOT(self, degree):
        """Prune higher order terms if expression is a polynomial
        so that resultant approximate expression has the desired degree."""

        coeffs = self.coeffs
        if len(coeffs) < degree:
            return self

        coeffs = coeffs[::-1]

        expr = sym.S.Zero
        var = self.var
        for m in range(degree + 1):
            term = coeffs[m].expr * var ** m
            expr += term

        return self.__class__(expr, **self.assumptions)            
    
    
def expr(arg, **assumptions):
    """Create Lcapy expression from arg.

    If arg is a string:
       If a t symbol is found in the string a tExpr object is created.
       If a s symbol is found in the string a sExpr object is created.
       If a f symbol is found in the string an fExpr object is created.
       If an omega symbol is found in the string an omegaExpr object is created.

    For example, v = expr('3 * exp(-t / tau) * u(t)')

    """

    from .sym import tsym, fsym, ssym, omegasym

    if isinstance(arg, (Expr, ExprList, ExprTuple, ExprDict)):
        return arg
    elif isinstance(arg, list):
        return ExprList(arg)
    elif isinstance(arg, tuple):
        return ExprTuple(arg)
    elif isinstance(arg, dict):
        return ExprDict(arg)    
    
    expr = sympify(arg, **assumptions)
    if expr.has(tsym):
        return tExpr(expr, **assumptions)
    elif expr.has(ssym):
        return sExpr(expr, **assumptions)
    elif expr.has(fsym):
        return fExpr(expr, **assumptions)
    elif expr.has(omegasym):
        return omegaExpr(expr, **assumptions)
    else:
        return cExpr(expr, **assumptions)


def symbol(name, **assumptions):
    """Create an Lcapy symbol.

    By default, symbols are assumed to be positive unless real is
    defined or positive is defined as False.

    """
    return Expr(symsymbol(name, **assumptions))


from .cexpr import cExpr        
from .fexpr import Hf, If, Vf, Yf, Zf, fExpr    
from .sexpr import Hs, Is, Vs, Ys, Zs, sExpr
from .texpr import tExpr
from .impedance import Impedance
from .admittance import Admittance
from .omegaexpr import Homega, Iomega, Vomega, Yomega, Zomega, omegaExpr

# Horrible hack to work with IPython around Sympy's back for LaTeX
# formatting.  The problem is that Sympy does not check for the
# _repr_latex method and instead relies on a predefined list of known
# types.  See _can_print_latex method in sympy/interactive/printing.py

import sys
try:
    from .printing import latex
    formatter = sys.displayhook.shell.display_formatter.formatters['text/latex']
    
    for cls in (ExprList, ExprTuple, ExprDict):
        formatter.type_printers[cls] = Expr._repr_latex_
except:
    pass
        
