from cns.data.constants import ANIMAL_IDS, ANIMAL_STATUS
from cns.data.trait_types import CTuple, CDate
from enthought.traits.api import HasTraits, Date, Enum, Instance, CList, \
    Property, Int, Str, CInt, CFloat, List, Any, Bool
import datetime

#from cns.experiment.paradigm import Paradigm
#from cns.experiment.data.experiment_data import ExperimentData

class Experiment(HasTraits):

    #paradigm = Instance(Paradigm, store='node')
    #data = Instance(ExperimentData, store='node')
    pass

class Animal(HasTraits):

    nyu_id = CInt(store='attribute', label='NYU ID')
    identifier = Enum(*ANIMAL_IDS, store='attribute')
    sex = Enum('U', 'M', 'F', store='attribute')
    birth = Date(store='attribute')
    parents = Str(store='attribute')
    age = Property(Int, depends_on='birth')
    processed = Bool(False)

    experiments = Property(List)
    name = Property(Str)

    def _get_experiments(self):
        try:
            return self._experiments
        except:
            try:
                from cns.data.persistence import get_objects
                filter = {'_v_name': 'aversive_date*' }
                exps = get_objects(self.store_node_source,
                                   self.store_node_path+'/experiments',
                                   filter=filter,
                                   child='Data',
                                   type=Experiment)
                self._experiments = exps
                return self._experiments
            except AttributeError:
                return []
    
    def _get_age(self):
        if self.birth is None:
            return -1
        else:
            td = datetime.date.today() - self.birth
            return td.days

    def __repr__(self):
        # Is this needed?
        try: date = self.birth.strftime('%Y_%m_%d')
        except: date = 'no_birth'
        template = 'Litter_%(parents)s_%(identifier)s_%(sex)s_%(date)s'
        return template % dict(date=date, parents=self.parents,
                               identifier=self.identifier, sex=self.sex)

    def __str__(self):
        return '%s %s NYU ID %d' % (self.identifier.capitalize(), self.sex,
                                    self.nyu_id)

    def _get_name(self):
        return '%s %s' % (self.identifier.capitalize(), self.sex)
    
class Cohort(HasTraits):

    description = Str(store='attribute')
    animals = List(Instance(Animal), store='child')
    size = Property(Int, depends_on='animals[]')

    def _get_size(self):
        return len(self.animals)

    def __str__(self):
        return '%s (n=%d)' % (self.description, self.size)
