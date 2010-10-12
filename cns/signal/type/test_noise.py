from cns.signal.type import Noise, AMNoise
from pylab import plot, show

if __name__ == '__main__':
    noise = Noise(amplitude=10, duration=0.2, fs=10e3)
    am = AMNoise(amplitude=10, depth=1, duration=0.2, fs=10e3)

    plot(am.t+noise.t[-1], am.signal, 'k')
    plot(noise.t, noise.signal, 'r')
    show()
