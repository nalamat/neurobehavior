from __future__ import division

from xml.etree import ElementTree as ET
from cns.experiment.data.aversive_data import AversiveData
from cns.channel import StaticChannel
import numpy as np
import scipy
import scipy.stats

def load_xml_data(fname):
    '''Imports legacy XML file format used for first generation of of the
    behavior program written by Brad Buran.  A TrialData object is returned
    which you can pass to an AnalyzedTrialObject for analysis.
    '''

    parameters = [ 'data.parameter_sequence',
                   'data.trial_sequence',
                   'data.timestamps',
                   'circuit.fs',
                   'data.lick_channel.signal',
                   'data.lick_channel.fs' ]

    data = get_parameters(fname, parameters)
    ts_info = np.array(data['data.timestamps'])/data['circuit.fs']

    par_info = map(lambda par, trial_num: [par]*int(trial_num),
                   data['data.parameter_sequence'],
                   data['data.trial_sequence'])
    par_info = np.concatenate(par_info)
    par_type = np.array(['safe']*len(par_info))

    if len(ts_info) != len(par_info):
        print len(ts_info), len(par_info)
        raise Exception

    warn_indices = np.array(data['data.trial_sequence']).cumsum().astype('i')-1
    par_type[warn_indices] = 'warn'

    trial_info = zip(ts_info, par_info, par_type)
    lick_data = StaticChannel(fs=data['data.lick_channel.fs'][0],
                              signal=data['data.lick_channel.signal'])

    data = AversiveData(contact_fs=data['data.lick_channel.fs'][0],
                        trial_data=trial_info,
                        contact_digital=lick_data)
    return data

def get_parameter(fname, element):

    def el_to_array(element):
        return [float(p) for p in element.text.split(',')]

    def get(element, data):
        try:
            base, rest = element.split('.', 1)
            return get(rest, data.find(base))
        except: return data.find(element)

    return el_to_array(get(element, ET.parse(fname)))

def get_parameters(fname, elements):
    '''Loads parameters from an XML file into a dictionary.
    '''
    data = [get_parameter(fname, e) for e in elements]
    #return dict(zip(elements, data))
    elements = [e.split('.')[-1] for e in elements]
    return np.rec.fromarrays(data, names=elements)

def group(data, keys):
    keys = np.array(keys)
    data = np.array(data, dtype=object)

    data_gr = {}
    for k in np.unique(keys):
        data_gr[k] = data[keys==k]
    return data_gr

def collate(files, key, filter=None):
    elements = ['data.parameter_sequence',
                'data.trial_sequence',
                'data.fa_sequence',
                'data.hit_sequence', ]

    groups = {}
    for f in files:
        print 'processing ' + f
        try:
            data = get_parameters(f, elements)
            k = get_parameter(f, key)[0]
            if filter is not None and filter(data):
	            try:
	                groups[k].append(data)
	            except KeyError:
	                groups[k] = [data]
        except:
            pass

    summary = {}
    for k, v in groups.items():
        data = np.concatenate(v).view(np.recarray)
        summary[k] = summarize_data(data, exclude=lambda x: x % 5)
        #summary[k] = data
    return summary
    #data = np.concatenate(data).view(np.recarray)
    #return summarize_data(data)

def summarize_data(data, exclude=None):

    def to_recarray(data):

        hit_trials  = lambda x: len(x.trial_sequence)
        fa_trials   = lambda x: x.trial_sequence.sum()-len(x)
        fa_num      = lambda x: x.fa_sequence.sum()
        hit_num     = lambda x: x.hit_sequence.sum()
        hit_prob    = lambda x: hit_num(x)/hit_trials(x)
        fa_prob     = lambda x: fa_num(x)/fa_trials(x)
        z_hit       = lambda x: scipy.stats.norm.ppf(hit_prob(x))
        z_fa        = lambda x: scipy.stats.norm.ppf(fa_prob(x))
        d           = lambda x: z_hit(x)-z_fa(x)

        calculations = [
                'hit_trials',
                'fa_trials',
                'fa_num',
                'hit_num',
                'hit_prob',
                'fa_prob',
                'z_hit',
                'z_fa',
                'd', ]

        results = [locals()[c](data) for c in calculations]
        return np.rec.fromarrays(results, names=calculations)
        #return results
    
    par_summary = []
    pars = np.unique(data.parameter_sequence)
    if exclude is not None:
        pars = [p for p in pars if not exclude(p)]
    for par in pars:
        mask = data.parameter_sequence == par
        par_summary.append(to_recarray(data[mask]))
    return pars, np.vstack(par_summary).view(np.recarray)

def indices(x, y):
    return np.array([np.flatnonzero(x==el) for el in y])

def align_array(x, y):
    new_x = np.unique(np.concatenate(x))
    new_y = np.ones((len(x), len(new_x))) * np.nan
    for i, (x_row, y_row) in enumerate(zip(x, y)):
        new_y[i, indices(new_x, x_row).ravel()] = y_row
    return new_x, new_y

z_hit = lambda x: scipy.stats.norm.ppf(x)
z_fa = lambda x: scipy.stats.norm.ppf(x)
d = lambda p, fa_frac: z_hit(p)-z_fa(fa_frac)

if __name__ == '__main__':
    file = r'C:\Users\Brad\Documents\Sanes\data\temporal integration\group 2/'
    #file += r'100413_fluffy_m.xml'
    file += r'100323_right_m.xml'
    data = load_xml_data(file)
    #analyzed = AnalyzedAversiveData(data=data, contact_offset=0.7)

    from pylab import *
    fill_between(-data.contact_digital.t, data.contact_digital.signal, 0)
    plot(data.warn_ts+0.7, [0.5]*len(data.warn_ts), 'r+', ms=25)
    plot(data.safe_ts+0.7, [0.5]*len(data.safe_ts), 'g+', ms=25)
    axis(xmin=20, xmax=90)
    show()
