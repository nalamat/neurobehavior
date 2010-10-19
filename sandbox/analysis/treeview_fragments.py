
from cns.data.type import Cohort, Animal
from enthought.traits.api import adapts, Instance
from enthought.traits.ui.api import View, Item, ITreeNode, ITreeNodeAdapter, TreeEditor

class CohortView(View):

    cohort = Instance('cns.data.type.Cohort')
    traits_view = View(Item('cohort', editor=TreeEditor(editable=False)))

class AnimalAdapter(ITreeNodeAdapter):
    
    adapts(Animal, ITreeNode)
    
    #-- ITreeNodeAdapter Method Overrides --------------------------------------

    def allows_children ( self ):
        return True

    def has_children ( self ):
        return len(self.adaptee.experiments) > 0

    def get_children ( self ):
        #return self.adaptee.experiments
        return []
        
    def get_label ( self ):
        return str(self.adaptee)
        
    def get_tooltip ( self ):
        return "FOO"
        
    def get_icon ( self, is_expanded ):
        if is_expanded:
            return '<open>'
        return '<item>'

    def can_auto_close ( self ):
        return True

class CohortAdapter(ITreeNodeAdapter):
    
    adapts(Cohort, ITreeNode)

    def allows_children ( self ):
        return True

    def has_children ( self ):
        return len(self.adaptee.animals) > 0

    def get_children ( self ):
        return self.adaptee.animals
        
    def get_label ( self ):
        return self.adaptee.description
        
    def get_tooltip ( self ):
        return "FOO"
        
    def get_icon ( self, is_expanded ):
        if is_expanded:
            return '<open>'
        return '<item>'

    def can_auto_close ( self ):
        return True

