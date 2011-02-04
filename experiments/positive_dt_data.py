from enthought.traits.api import List, Tuple, Float, Int, Str, Property

from positive_data import PositiveData

class PositiveDTData(PositiveData):

    # This is a nested datatype
    TRIAL_DTYPE = [
            ('parameter', [
                ('duration', 'f'), 
                ('attenuation', 'f')
                ]),
            ('ts_start', 'i'), 
            ('ts_end', 'i'),
            ('type', 'S4'), 
            ('response', 'S16'), 
            ('reaction_time', 'f'),
            ]

    trial_log = List(Tuple(
                        Tuple(Float, Float), 
                        Int, Int, Str, Str, Float
                        ),
                     store='table', dtype=TRIAL_DTYPE)

    PAR_INFO_DTYPE = [
            ('parameter', [
                ('duration', 'f'),
                ('attenuation', 'f'),
                ]),
            ('nogo_count', 'i'),
            ('go_count', 'i'),
            ('fa_count', 'i'),
            ('hit_count', 'i'),
            ('hit_frac', 'f'),
            ('fa_frac', 'f'),
            ('d', 'f'),
            ]

    par_info = Property(store='table', dtype=PAR_INFO_DTYPE)

    def _get_par_info(self):
        return zip(self.pars, self.par_nogo_count, self.par_go_count,
                self.par_fa_count, self.par_hit_count, self.par_fa_frac,
                self.par_hit_frac, self.par_dprime)
