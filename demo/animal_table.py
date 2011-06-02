from cns.data.view import CohortEditDialog
from cns.data.type import Cohort, Animal

c = Cohort(description='Control Group 1',
           animals=[Animal(parents='HH', identifier='tail'),
                    Animal(parents='HH', identifier='fluffy'),])
            
CohortEditDialog().configure_traits()
CohortEditDialog(cohort=c, editable=False).configure_traits()
