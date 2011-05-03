''' Created on Apr 26, 2010

@author: admin_behavior
'''

from cns import calibrate
from cns import signal
from pylab import plot, show

    
def do_plot():
    a = 5
    tone = signal.type.Tone(frequency=500, amplitude=a)
    fm = signal.type.FMTone(fc=500, fm=5, delta_fc_max=20, amplitude=a)
    am = signal.type.AMTone(fc=500, fm=5, env_depth=0.3, amplitude=a)
    i = 2e3
    #t, s = calibrate.level_cal(tone, atten=10, mic_sens=11.6e-3)
    kw = dict(atten=0, mic_sens=11.6e-3)
    
    t, s = calibrate.level_cal(tone, **kw)
    m = (t>=0.25)&(t<0.65)
    plot(t[m], s[m], label='tone')
    print 'tone', max(s[m])-min(s[m]), 'dB'
    
    t, s = calibrate.level_cal(fm, **kw)
    print 'fm', max(s[m])-min(s[m]), 'dB'
    plot(t[m], s[m], label='fm')
    
    t, s = calibrate.level_cal(am, **kw)
    print 'am', max(s[m])-min(s[m]), 'dB'
    plot(t[m], s[m], label='am')
    
    show()
    
def do_comp_tones():
    am1 = signal.type.AMTone(env_depth=0.5, amplitude=2, fs=10e3)
    am2 = signal.type.AMTone(env_depth=0.5, amplitude=1, fs=10e3)
    plot(am1.t, am1.signal, 'g')
    plot(am2.t, am2.signal, 'r')
    show()
    
if __name__ == '__main__':
    do_plot()