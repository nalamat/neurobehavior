from positive_data import PositiveData

class PositiveDTData(PositiveData):

    TRIAL_DTYPE = [('parameter', 'f'), ('ts_start', 'i'), ('ts_end', 'i'),
                   ('type', 'S4'), ('response', 'S16'), ('reaction_time', 'f'),
                   ('attenuation', 'f')]

    trial_log = List(Tuple(Float, Int, Int, Str, Str, Float, Float),
                     store='table', dtype=TRIAL_DTYPE)

    def log_trial(self, ts_start, ts_end, ttype, parameter, attenuation):

        ts_start = int(ts_start)
        ts_end = int(ts_end)

        poke_data = self.poke_TTL.get_range_index(ts_start, ts_end)
        spout_data = self.spout_TTL.get_range_index(ts_start, ts_end)
        if poke_data.all():
            response = 'no withdraw'
        elif spout_data.any():
            response = 'spout'
        elif poke_data[-1] == 1:
            response = 'poke'
        else:
            response = 'no response'

        try:
            if response == 'spout':
                reaction_time = ts(edge_rising(spout_data))[0]/self.spout_TTL.fs
            elif response == 'poke':
                reaction_time = ts(edge_rising(poke_data))[0]/self.poke_TTL.fs
            else:
                reaction_time = -1
        except:
            reaction_time = -1
            
        data = parameter, ts_start, ts_end, ttype, response, reaction_time, \
            attenuation
        self.trial_log.append(data)
