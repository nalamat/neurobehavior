from enthought.traits.api import HasTraits, Bool, on_trait_change, Dict, Event, List, Any
from evaluate import evaluate_expressions, evaluate_value

import logging
log = logging.getLogger(__name__)

class ApplyRevertControllerMixin(HasTraits):
    '''
    If an experiment is running, we need to queue changes to most of the
    settings in the GUI to ensure that the user has a chance to finish making
    all the changes they desire before the new settings take effect.
    
    Supported metadata
    ------------------
    ignore
        Do not monitor the trait for changes
    immediate
        Apply the changes immediately (i.e. do not queue the changes)
        
    Handling changes to a parameter
    -------------------------------
    When a parameter is modified via the GUI, the controller needs to know how
    to handle this change.  For example, changing the pump rate or reward
    volume requires sending a command to the pump via the serial port.
    
    When a change to a parameter is applied, the class instance the parameter
    belongs to is checked to see if it has a method, "set_parameter_name",
    defined. If not, the controller checks to see if it has the method defined
    on itself.
    
    The function must have the following signature set_parameter_name(self, value)
    '''

    pending_changes = Bool(False)
    shadow_paradigm = Any
    pending_expressions = Dict
    current_context = Dict
    context_labels = Dict
    context_log = Dict
    old_context = Dict

    # List of name, value, label tuples (used for displaying in the GUI)
    current_context_list = List

    @on_trait_change('model.paradigm.+container*.+context')
    def handle_change(self, instance, name, old, new):
        print 'detected change', instance, name
        # When a paradigm value has changed while the experiment is running,
        # indicate that changes are pending
        if self.state != 'halted':
            log.debug('Detected change to %s', name)
            self.pending_changes = True

    def invalidate_context(self):
        '''
        Invalidate the current context.  This forces the program to reevaluate
        any values that may have changed.
        '''
        # Once the context has been invalidated, we need to reevaluate all
        # expressions so we add the current expressions to the pending
        # expressions "stack".
        log.debug('Invalidating context')
        self.old_context = self.current_context.copy()
        self.current_context = self.model.data.trait_get(context=True)
        self.pending_expressions = self.shadow_paradigm.trait_get(context=True)

    def apply(self, info=None):
        log.debug('Applying requested changes')
        try:
            # First, we do a quick check to ensure the validity of the
            # expressiosn the user entered by evaluating them.  If the
            # evaluation passes, we will make the assumption that the
            # expressiosn are valid as entered.  However, this will *not* catch
            # all edge cases or situations where actually applying the change
            # causes an error.
            pending_expressions = self.model.paradigm.trait_get(context=True)
            current_context = self.model.data.trait_get(context=True)
            evaluate_expressions(pending_expressions, current_context)

            # If we've made it this far, then let's go ahead and copy the
            # changes over.  We'll apply them as well if a trial is not
            # currently running.
            self.shadow_paradigm.copy_traits(self.model.paradigm)
            if self.request_pause():
                self.trigger_next()
                self.request_resume()
            self.pending_changes = False
        except Exception, e:
            # A problem occured when attempting to apply the context. 
            # the changes and notify the user.  Hopefully we never reach this
            # point.
            log.exception(e)
            mesg = '''
            Unable to apply your requested changes due to an error. No changes
            have been made. Please review the changes you have requested to
            ensure that they are indeed valid.\n\n''' + str(e)
            import textwrap
            textwrap.dedent(mesg)
            error(info.ui.control, message=mesg, title='Error applying changes')

    def revert(self, info=None):
        '''
        Revert GUI fields to original values
        '''
        log.debug('Reverting requested changes')
        self.model.paradigm = self.shadow_paradigm.clone_traits()
        self.pending_changes = False
    
    def get_current_value(self, name):
        '''
        Get the current value of a context variable.  If the context variable
        has not been evaluated yet, compute its value from the
        pending_expressions stack.  Additional context variables may be
        evaluated as needed.
        '''
        try:
            return self.current_context[name]
        except:
            evaluate_value(name, self.pending_expressions, self.current_context)
            return self.current_context[name]

    def evaluate_pending_expressions(self, extra_context=None):
        '''
        Evaluate all pending expressions and store results in current_context.

        If extra_content is provided, it will be included in the local
        namespace. If extra_content defines the value of a parameter also
        present in pending_expressions, the value stored in extra_context takes
        precedence.
        '''
        log.debug('Evaluating pending expressions')
        if extra_context is not None:
            self.current_context.update(extra_context)
        self.current_context.update(self.model.data.trait_get(context=True))
        evaluate_expressions(self.pending_expressions, self.current_context)

    @on_trait_change('current_context_items')
    def _apply_context_changes(self, event):
        '''
        Automatically apply changes as expressions are evaluated and their
        result added to the context
        '''
        for name, value in event.added.items():
            log.debug('Change detected to context variable %s', name)
            old_value = self.old_context.get(name, None)
            if self.old_context.get(name, None) != value:
                self._apply_context_value(name, value)
        for name, value in event.changed.items():
            log.debug('Change detected to context variable %s', name)
            if self.old_context.get(name, None) != value:
                self._apply_context_value(name, value)

    def _apply_context_value(self, name, value):
        try:
            getattr(self, 'set_{}'.format(name))(value)
            log.debug('Setting %s', name)
        except AttributeError, e:
            log.warn(str(e))

    @on_trait_change('current_context_items')
    def _update_current_context_list(self):
        context = []
        for name, value in self.current_context.items():
            label = self.context_labels.get(name, '')
            changed = not self.old_context.get(name, None) == value
            log = self.context_log[name]
            context.append((name, value, label, log, changed))
        self.current_context_list = sorted(context)
        
    def initialize_context(self):
        for instance in (self.model.data, self.model.paradigm):
            for name, trait in instance.traits(context=True).items():
                self.context_labels[name] = trait.label
                self.context_log[name] = trait.log
        self.shadow_paradigm = self.model.paradigm.clone_traits()
