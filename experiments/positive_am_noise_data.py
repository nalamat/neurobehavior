from enthought.traits.api import List, Tuple, Float, Int, Str, Property
from positive_data import PositiveData

class PositiveAMNoiseData(PositiveData):

    # This is a nested datatype
    TRIAL_DTYPE = [
            ('parameter', 'f'),
            ('ts_start', 'i'), 
            ('ts_end', 'i'),
            ('type', 'S4'), 
            ('response', 'S16'), 
            ('response_time', 'f'),
            ('reaction_time', 'f'),
            ('modulation_onset', 'f'),
            ]

    trial_log = List(Tuple(Float, Int, Int, Str, Str, Float, Float, Float),
                     store='table', dtype=TRIAL_DTYPE)

    def log_trial(self, ts_start, ts_end, ttype, parameter, modulation_onset):
        resp, resp_time, react_time = self.compute_response(ts_start, ts_end)
        self.trial_log.append((parameter, int(ts_start), int(ts_end), ttype,
            resp, resp_time, react_time, modulation_onset))
