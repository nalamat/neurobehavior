from positive_data import PositiveData

class PositiveDTData(PositiveData):

    TRIAL_DTYPE = [('parameter', [
                        ('duration', 'f'), 
                        ('attenuation', 'f')
                        ]),
                   ('ts_start', 'i'), 
                   ('ts_end', 'i'),
                   ('type', 'S4'), 
                   ('response', 'S16'), 
                   ('reaction_time', 'f'),
                   ]

    trial_log = List(Tuple(Tuple(Float, Float), 
                     Int, Int, Str, Str, Float, Float),
                     store='table', dtype=TRIAL_DTYPE)
