from neurogen.blocks import load_dict
from neurogen.trait_interface import block_view_factory

am_noise = load_dict((
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
            }))

ramped_am_noise = load_dict((
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
            }))

ramped_tone = load_dict((
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
        ))

am_noise = block_view_factory(am_noise)()
am_noise.variable = 'SAM_1__depth'
ramped_am_noise = block_view_factory(ramped_am_noise)()
ramped_am_noise.variable = 'SAM_2__depth'
ramped_tone = block_view_factory(ramped_tone)()
ramped_tone.variable = 'Cos2Envelope_2__duration'

signal_options = {
        ramped_tone     : 'Ramped Tone',
        ramped_am_noise : 'Ramped AM Noise',
        am_noise        : 'AM Noise',
        }
