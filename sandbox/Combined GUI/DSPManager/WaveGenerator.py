import numpy

class WaveGenerator():
    def __init__(self, waveFreq=4e3, waveAmplitude=1, samplingFrequency=44100, samplingSize=44100):
        self.waveFreq=waveFreq
        self.waveAmplitude=waveAmplitude
        self.samplingFrequency = samplingFrequency
        self.samplingSize = samplingSize
        self.__currentSampleCounter = 0
    
    def reset(self):
        self.__currentSampleCounter = 0
    
    def next(self):
        toReturn = self.waveAmplitude * numpy.sin(2*numpy.pi * self.waveFreq * (numpy.arange(self.samplingSize) + self.__currentSampleCounter)/float(self.samplingFrequency))
        self.__currentSampleCounter += self.samplingSize
        return toReturn
    
    def setSamplingFrequency(self, samplingFrequency):
        self.samplingFrequency = samplingFrequency
    
    def setSamplingSize(self, samplingSize):
        self.samplingSize=samplingSize
