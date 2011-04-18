import numpy as np
from enthought.traits.ui.api import (TextEditor, View, Item, BooleanEditor,
        CompoundEditor)
from enthought.traits.api import Callable, HasTraits, Instance

class ParameterExpression(object):

    GLOBALS = {
            'arange':   np.arange,
            'randint':  np.random.randint,
            'uniform':  np.random.uniform,
            }

    def __init__(self, string):
        self.string = str(string)
        self.code = compile(self.string, '<string>', 'eval')
        try:
            # Do a quick check to see if any syntax errors pop out.  NameError
            # is going to be a common one (especially when we are making it
            # dependent on other modules).
            self.eval()
        except NameError:
            pass

    def eval(self, context=None):
        return eval(self.code, self.GLOBALS, context)

    def __str__(self):
        return self.string

def evaluate_parameters(parameters, extra_context=None):
    context = {}
    if extra_context is not None:
        context.update(extra_context)
    to_evaluate = list(parameters.items())

    remaining = len(to_evaluate)

    while True:
        pending = []
        for parameter, expression in to_evaluate:
            if isinstance(expression, ParameterExpression):
                try:
                    context[parameter] = expression.eval(context)
                except NameError, e:
                    # We're ok with NameErrors since the parameter likely requires
                    # some context to evaluate properly
                    pending.append((parameter, expression))
            else:
                context[parameter] = expression

        if len(pending) == 0:
            return context
        elif len(pending) == remaining:
            raise ValueError, "Circular dependency found"
        else:
            to_evaluate = pending
            pending = []

class ExpressionEditor(TextEditor):

    evaluate = Callable(ParameterExpression)

from enthought.traits.api import TraitType

class ExpressionTrait(TraitType):

    store = 'attribute'

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
    test.configure_traits()
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
            'j':    32,
            'k':    65,
            'l':    ParameterExpression('j+k'),
            }
    print evaluate_parameters(parameters)
