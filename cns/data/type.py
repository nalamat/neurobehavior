from enthought.traits.api import HasTraits, Date, Enum, Instance, \
    Property, Int, Str, List, Bool
import datetime

class Animal(HasTraits):

    nyu_id      = Int(store='attribute', label='Animal ID')

    # Eventually we should switch over to animal_id, but we leave nyu_id in
    # until experiments using older versions of the file are done running.
    animal_id   = Property(depends_on='nyu_id', store='attribute')
    identifier  = Str(store='attribute')
    sex         = Enum('U', 'M', 'F', store='attribute')
    birth       = Date(store='attribute')
    parents     = Str(store='attribute')
    age         = Property(Int, depends_on='birth')

    # Defining animal_id as a Property and providing the get/set methods which
    # update nyu_id effectively makes animal_id an alias for nyu_id
    def _get_animal_id(self):
        return self.nyu_id

    def _set_animal_id(self, value):
        self.nyu_id = value

    processed   = Bool(False)

    #experiments = Property(List)
    name        = Property(Str)
    
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
    animals     = List(Instance(Animal), store='child')
    size        = Property(Int, depends_on='animals[]')

    def _get_size(self):
        return len(self.animals)

    def __str__(self):
        return '%s (n=%d)' % (self.description, self.size)
