import numpy as np
from enthought.traits.ui.api import (TextEditor, View, Item, BooleanEditor,
        CompoundEditor)
from enthought.traits.api import Callable, HasTraits, Instance

'''
Available attributes for evaluating experiment parameters.

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
        Ensure value falls within
        
    '''
        

def choice(sequence):
    i = np.random.randint(0, len(sequence))
    return sequence[i]

class ParameterExpression(object):

    GLOBALS = {
            'random':       np.random,
            'arange':       np.arange,
            'randint':      np.random.randint,
            'uniform':      np.random.uniform,
            'exponential':  np.random.exponential,
            'clip':         np.clip,
            'choice':       choice,
            'toss':         lambda x: np.random.uniform() <= x,
            }

    def __init__(self, string):
        self.string = str(string)
        self._code = compile(self.string, '<string>', 'eval')
        try:
            # Do a quick check to see if any syntax errors pop out.  NameError
            # is going to be a common one (especially when we are making it
            # dependent on other modules).
            self.eval()
        except NameError:
            pass

    def eval(self, context=None):
        return eval(self._code, self.GLOBALS, context)

    def __str__(self):
        return self.string

    def __getstate__(self):
        '''
        Code objects cannot be pickled
        '''
        state = self.__dict__.copy()
        del state['_code']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._code = compile(self.string, '<string>', 'eval')

def eval_context(parameters, extra_context=None):
    context = {}
    if extra_context is not None:
        context.update(extra_context)
    parameters = parameters.copy()
    for key in context:
        if key in parameters:
            del parameters[key]

    pending = list(parameters.items())
    while True:
        failed = []
        num_pending = len(pending)
        for parameter, expression in pending:
            if isinstance(expression, ParameterExpression):
                try:
                    context[parameter] = expression.eval(context)
                except NameError, e:
                    failed.append((parameter, expression))
            else:
                context[parameter] = expression

        if len(failed) == 0:
            return context
        elif len(failed) == num_pending:
            raise ValueError, "Circular dependency found"
        else:
            pending = failed

class ExpressionEditor(TextEditor):

    evaluate = Callable(ParameterExpression)

from enthought.traits.api import TraitType

class ExpressionTrait(TraitType):

    metadata = { 'store': 'attribute' }

    def validate(self, object, name, value):
        if isinstance(value, ParameterExpression):
            return value
        self.error(object, name, value)

    def create_editor(self):
        return ExpressionEditor()

    def init(self):
        if not isinstance(self.default_value, ParameterExpression):
            self.default_value = ParameterExpression(self.default_value)

if __name__ == '__main__':
    class TestEditor(HasTraits):
        expression = ExpressionTrait('randint(1, 2)')
        traits_view = View(Item('expression'))
    test = TestEditor()
    #test.configure_traits()
    print test.expression.eval()

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
    print evaluate_parameters(parameters)
