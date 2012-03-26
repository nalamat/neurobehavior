'''
    random
        Numpy's random module.  Provides access to all the functions and
        distributions available within this module.
    arange
    randint(low, high)
        Return random integer within the range [low, high]
    uniform(low, high)
        Draw sample from uniform distribution in the interval [low, high)
    exponential(scale)
        Draw sample from exponential distribution with scale parameter (i.e.
        :math:`\\beta')
    clip(value, lb, ub)
        Ensure value falls within bounds
    '''

from __future__ import division

import ast
import numpy as np
from traits.api import HasTraits, on_trait_change, TraitType

import logging
log = logging.getLogger(__name__)

def choice(sequence):
    i = np.random.randint(0, len(sequence))
    return sequence[i]

def random_speaker(bias=0.5):
    return 'primary' if np.random.uniform() <= bias else 'secondary'

def h_uniform(x, lb, ub):
    '''
    Assuming a uniform distribution, return the probability of an event occuring
    at that given sample (i.e. the hazard probability).

    >>> h_uniform(0, 3, 7)
    0.0
    >>> h_uniform(3, 3, 7)
    0.25
    >>> h_uniform(4, 3, 7)
    0.3333333333333333
    >>> h_uniform(6, 3, 7)
    1.0
    >>> h_uniform(7, 3, 7)
    1.0
    '''
    if x < lb:
        return 0.0
    if x >= ub:
        return 1.0
    return 1.0/(ub-x)

def toss(x=0.5):
    '''
    Flip a coin weighted by x
    '''
    return np.random.uniform() <= x

def get_dependencies(string):
    '''
    Parse a Python expression to determine what names are required to evaluate
    it.  Useful for determining dependencies.

    >>> get_dependencies('x+1')
    ('x',)

    >>> get_dependencies('32**0.5')
    ()

    >>> get_dependencies('sqrt(x)+y')
    ('sqrt', 'x', 'y')

    >>> get_dependencies('range(x)+numpy.random()')
    ('numpy', 'range', 'x')

    '''
    tree = ast.parse(string)
    result = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
    result.sort()
    return tuple(result)

class ParameterExpression(object):

    GLOBALS = {
            'random':           np.random,
            'arange':           np.arange,
            'randint':          np.random.randint,
            'uniform':          np.random.uniform,
            'exponential':      np.random.exponential,
            'clip':             np.clip,
            'choice':           choice,
            'toss':             toss,
            'random_speaker':   random_speaker,
            'h_uniform':        h_uniform,
            }

    def __init__(self, value):
        if isinstance(value, basestring):
            self._expression = value
            self._code = compile(self._expression, '<string>', 'eval')
            self._dependencies = get_dependencies(self._expression)
            self._cache_valid = False
            self._cached_value = None

            try:
                # Do a quick check to see if any syntax errors pop out.
                # NameError is going to be a common one (especially when we are
                # making it dependent on other modules).  If we can successfully
                # evaluate it and it does not depend on any values, then we
                # might as well cache the resulting value.
                result = eval(self._code, self.GLOBALS)

                if not self._dependencies:
                    # If the code has no dependencies, then we can evaluate it
                    # once and use the cached value.  If the code has
                    # dependencies (even if it's in the globals dict, then we
                    # need to reevaluate it each time the value is requested
                    # just in case the globals function returns a random value).
                    self._cache_valid = True
                    self._cached_value = result

            except NameError:
                # This is the one error we will allow since it may suggest the
                # expression requires values not present in the global
                # namespace (but we don't know that for sure ...)
                pass
        else:
            self._dependencies = []
            self._expression = str(value)
            self._cache_valid = True
            self._cached_value = value
            self._code = None

    def evaluate(self, local_context=None):
        if self._cache_valid:
            return self._cached_value
        else:
            return eval(self._code, self.GLOBALS, local_context)

    def __str__(self):
        return self._expression

    def __repr__(self):
        return "{} ({})".format(self._expression, self._cache_valid)

    # One must define both the == and != rich comparision methods for
    # on_trait_change to properly register trait changes while ignoring
    # situations where two ParameterExpressions have identical values.
    def __eq__(self, other):
        if not isinstance(other, ParameterExpression):
            return NotImplemented
        return self._expression == other._expression

    def __ne__(self, other):
        if not isinstance(other, ParameterExpression):
            return NotImplemented
        return self._expression != other._expression

    def __getstate__(self):
        '''
        Code objects cannot be pickled
        '''
        state = self.__dict__.copy()
        del state['_code']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if not self._cache_valid:
            self._code = compile(self._expression, '<string>', 'eval')
        else:
            self._code = None

def evaluate_value(parameter, expressions, context=None):
    '''
    Given a stack of expressions and the desired parameter to evaluate,
    evaluates all the expressions necessary to evaluate the desired parameter.
    If an expression is evaluated, it is removed from the stack of expressions
    and added to the context.
    '''
    if context is None:
        context = {}

    if parameter in context:
        del expressions[parameter]
        return context

    expression = expressions[parameter]
    del expressions[parameter]

    if isinstance(expression, ParameterExpression):
        for d in expression._dependencies:
            if d in expressions:
                evaluate_value(d, expressions, context)
        context[parameter] = expression.evaluate(context)
    else:
        context[parameter] = expression
    return context

def evaluate_expressions(expressions, current_context):
    '''
    Will raise a NameError if it is no longer able to evaluate.
    '''
    while expressions:
        name = expressions.keys()[0]
        evaluate_value(name, expressions, current_context)

class Expression(TraitType):

    info_text = 'a Python value or expression'
    default_value = ParameterExpression('None')

    def post_setattr(self, object, name, value):
        if not isinstance(value, ParameterExpression):
            value = ParameterExpression(value)
            object.__dict__[name] = value

    def init(self):
        if not isinstance(self.default_value, ParameterExpression):
            self.default_value = ParameterExpression(self.default_value)

    def validate(self, object, name, value):
        if isinstance(value, ParameterExpression):
            return value
        try:
            return ParameterExpression(value)
        except:
            self.error(object, name, value)

import unittest

class TestExpressions(unittest.TestCase):

    parameters = {
            'a':    ParameterExpression('5'),
            'b':    ParameterExpression('6'),
            'c':    ParameterExpression('a*5'),
            'd':    ParameterExpression('a*b+c'),
            'e':    ParameterExpression('d+c'),
            'f':    ParameterExpression('1.23'),
            'g':    ParameterExpression('range(a, b)'),
            'h':    ParameterExpression('randint(5, 6)'),
            'i':    ParameterExpression('uniform(1, 5)'),
            #'j':    ParameterExpression('l'),
            'j':    57,
            'k':    65,
            'l':    ParameterExpression('j+k'),
            }

    evaluate_value_tests = [
            ('a', {}, {'a': 5}),
            ('b', {}, {'b': 6}),
            ('c', {}, {'a': 5, 'c': 25}),
            ('d', {}, {'a': 5, 'b': 6, 'c': 25, 'd': 55}),
            ('d', {'a': 4}, {'a': 4, 'b': 6, 'c': 20, 'd': 44}),
            ('h', {}, {'h': 5}),
            ]

    def test_evaluate_value(self):
        for parameter, extra_context, expected in self.evaluate_value_tests:
            parameters = self.parameters.copy()
            actual = evaluate_value(parameter, parameters, extra_context)
            self.assertEqual(expected, actual)

            for parameter in expected:
                self.assertTrue(parameter not in parameters)

    def test_equal(self):
        a = ParameterExpression('a+b')
        b = ParameterExpression('a+b')
        self.assertEqual(a, b)

    def test_assignment(self):
        obj = TestTraits()
        obj.a = 'a+5'

class TestTraits(HasTraits):
     
    a = Expression('a+4', context=True)

    @on_trait_change('a')
    def print_change(self):
        print 'changed'

if __name__ == '__main__':
    pass
    #parameters = {'a': ParameterExpression('1'), 'b': ParameterExpression('a')}
    #evaluate_value('a', parameters)
    #context = {}
    #evaluate_expressions(parameters, context)
    #print parameters, context
    #import doctest
    #doctest.testmod()
    #unittest.main()
    #t = TestTraits()
    #t.a = ParameterExpression('b+4')
    #t.a = ParameterExpression('b+4')
    #t.a = ParameterExpression('b+4')
    #t.a = 'b+4'
