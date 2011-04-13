import numpy as np
from enthought.traits.ui.api import TextEditor, View, Item
from enthought.traits.api import Callable, HasTraits, Instance

class ParameterExpression(object):

    GLOBALS = {
            'arange':   np.arange,
            'randint':  np.random.randint,
            'uniform':  np.random.uniform,
            }


    def __init__(self, string):
        self.string = string
        self.code = compile(string, '<string>', 'eval')
        try:
            # Do a quick check to see if any syntax errors pop out.  NameError
            # is going to be a common one (especially when we are making it
            # dependent on other modules).
            self.eval({})
        except NameError:
            pass

    def eval(self, context):
        return eval(self.code, self.GLOBALS, context)

    def __str__(self):
        return self.string

def evaluate_parameters(parameters, extra_context=None):
    context = {}
    if extra_context is not None:
        context.update(extra_context)

    to_evaluate = list(parameters.items())
    maxiter = len(to_evaluate) * 5
    i = 0

    while len(to_evaluate) > 0 and i < maxiter:
        parameter, expression = to_evaluate.pop(0)
        if isinstance(expression, ParameterExpression):
            try:
                context[parameter] = expression.eval(context)
            except NameError, e:
                to_evaluate.append((parameter, expression))
        else:
            context[parameter] = expression
            
        i += 1
    if len(to_evaluate) > 0:
        raise ValueError, "Circular dependency found"
    else:
        return context

class ExpressionEditor(TextEditor):

    evaluate = Callable(ParameterExpression)

from enthought.traits.api import TraitType

class ExpressionTrait(TraitType):

    def validate(self, object, name, value):
        if isinstance(value, ParameterExpression):
            return value
        self.error(object, name, value)

    def create_editor(self):
        return ExpressionEditor()

if __name__ == '__main__':
    class TestEditor(HasTraits):
        expression = ExpressionTrait()
        traits_view = View(Item('expression'))
    test = TestEditor()
    #test.configure_traits()
    print test.expression

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
            }
    print evaluate_parameters(parameters)
