'''
Created on May 18, 2010

@author: admin_behavior
'''

from cns import calibrate
import numpy as np
from pylab import plot, show, legend, xlabel, ylabel, title
from cns.signal.type import Silence, Noise

attens = [0, 10, 20]
#crown = [0, 20, 40]
crown = [0, 20]
sens = 0.0071711810928633503 # Vrms/Pa

def noise():
    #l, p, r = calibrate.tone_cal(4000, duration=0.5, rec_delay=0.1, mic_sens=sens,
    #                             atten=0, averages=1, fft=True)
    r = calibrate.spec_cal(Noise(duration=15), mic_sens=sens,
                                 atten=0, averages=1)
    calibrate.plot_cal(r)

def cal_sweep():
    #sens, result = calibrate.ref_cal(fft=False, mode='conv')
    result = np.zeros((len(crown), len(attens)))
    for i, c in enumerate(crown):
        raw_input('Have you set crown to %d' % c)
        for j, atten in enumerate(attens):
            l, p = calibrate.tone_cal(2000, duration=0.5, rec_delay=0.1, 
                               mic_sens=sens,
                               atten=atten,
                               averages=1)
            result[i, j] = l
    np.savetxt('crossover_2000Hz.txt', result, delimiter='\t')
    
def plot_sweep():
    data = np.loadtxt('crossover_2000Hz.txt', delimiter='\t')
    for i, c in enumerate(crown):
        plot(attens, data[i], label='%d' % c)
    xlabel('PA5 attenuation')
    ylabel('Speaker output')
    title('Linearity of Amplifier and Attenuator at 2000 Hz')
    legend()
    show()
    
if __name__ == '__main__':
    #cal_sweep()
    #plot_sweep()
    noise()