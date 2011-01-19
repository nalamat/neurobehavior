from neurogen.blocks import load_dict
from neurogen.trait_interface import block_view_factory

am_noise = (
        'Output', {
                'token': (
                    'SAM', {
                        'token': (
                            'BandlimitedNoise', {
                                'seed'      : -1,
                                'fc'        : 25e3,
                                'bandwidth' : 20e3,
                                'amplitude' : 1,
                                'label'     : 'Noise Carrier',
                                }),
                        'depth'          : 0.5,
                        'frequency'      : 5,
                        'equalize_power' : True,
                        'equalize_phase' : True,
                        'label'          : 'Sinusoidal Modulator',
                        }),
            #'label'     : 'Waveform',
            })

ramped_am_noise = (
        'Output', {
            'token': (
                'Cos2Envelope', {
                    'token': (
                        'SAM', {
                            'token': (
                                'BroadbandNoise', {
                                    'seed'      : -1,
                                    #'fc'        : 25e3,
                                    #'bandwidth' : 20e3,
                                    'amplitude' : 1,
                                    'label'     : 'Noise Carrier',
                                    }),
                            'depth'          : 0.5,
                            'frequency'      : 5,
                            'equalize_power' : True,
                            'equalize_phase' : True,
                            'label'          : 'Sinusoidal Modulator',
                            }),
                        }),
            #'label'     : 'Waveform',
            })

tone = (
        'Output', {
            'token': (
                'Cos2Envelope', {
                    'rise_duration' :   0.25,
                    'duration'      :   1,
                    'token' : (
                        'Tone', {
                            'frequency' : 1e3,
                            'amplitude' : 1,
                            'label'     : 'Tone',
                            }),
                    'label': 'Envelope',
                    }),
            'label'     : 'Waveform',
            }
        )

ramped_am_noise_signal = load_dict(ramped_am_noise)
am_noise_signal = load_dict(am_noise)
tone_signal = load_dict(tone)

sig = block_view_factory(am_noise_signal)()
sig.variable = 'SAM_2__depth'

sig2 = block_view_factory(ramped_am_noise_signal)()
sig2.variable = 'SAM_1__depth'

signal_options = {
        sig2  : 'Ramped AM Noise',
        sig   : 'AM Noise',
        block_view_factory(tone_signal)()       : 'Ramped Tone'
        }
