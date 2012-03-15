import Listener
import time
from cns import equipment
import numpy
class FakeInterface:
    def __init__(self, waveGenerator, uploadBlockSize, minBufferSize=None):
        self.waveGenerator = waveGenerator
        self.uploadBlockSize = uploadBlockSize
        self.minBufferSize = minBufferSize
        self.maxBufferSize = 400000
        self.listener = Listener.Listener(self.uploadNextBlock, self.checkForNextUpload, 0.1)
        self.filledBufferPosition = 0
        self.circuitBufferPosition = 0
        self.uploadNextBlock()
        
    def checkForNextUpload(self):
        circuitBufferPosition = self.circuitBufferPosition
        filledBufferPosition = self.filledBufferPosition
        if circuitBufferPosition > self.filledBufferPosition: #Then we assume that the filled Buffer has wrapped around the DSP, but the sound being played has yet to wrap around the buffer
            filledBufferPosition += self.maxBufferSize
        if filledBufferPosition - circuitBufferPosition <= self.minBufferSize:
            return True
        return False
    def uploadNextBlock(self):
        print "Uploading Next Block Now!"
        upload = self.waveGenerator.next()
        if len(upload) + self.filledBufferPosition < self.maxBufferSize:
            #self.circuit.uploadBuffer(upload)
            self.filledBufferPosition += len(upload)
        else:
            #self.circuit.uploadBuffer(upload[:self.maxBufferSize - self.filledBufferPosition])
            #self.circuit.uploadBuffer(0, upload[self.maxBufferSize-self.filledBufferPosition:])
            self.filledBufferPosition = len(upload) - (self.maxBufferSize - self.filledBufferPosition)
        
    def start(self):
        self.listener.start()
        print 'start'
        while True:
            self.circuitBufferPosition += 25000
            self.circuitBufferPosition %= self.maxBufferSize
            print "CircuitPosition:",self.circuitBufferPosition,"Loaded Buffer Position:",self.filledBufferPosition
            time.sleep(0.25)
        #self.circuit.trigger(1)
    
    #def stop():
    #   self.circuit.trigger(2)     

class SimpleDSPInterface:
    def __init__(self):
        self.dsp = equipment.dsp()
        self.circuit = self.dsp.load('RepeatPlay_v2','RX6')
        #self.samplingFrequency = self.circuit.fsvalue
        self.samplingFrequency = self.circuit.fs
        self.maxBufferSize = self.circuit.sig_n.value
        self.circuit.start()
        #self.circuit.play_dur_n.value = 1
       
    def uploadBuffer(self, buffer):
    	duration = len(buffer)/float(self.samplingFrequency)
    	self.circuit.play_dur_n.set(duration, src_unit='s')
        self.circuit.sig.WriteTagV(0, buffer)
    
    def getSamplingRate(self):
    	return self.samplingFrequency
    
    def start(self):
    	self.circuit.sig_idx.value = 0
        self.circuit.start()
        self.circuit.trigger(1)
    
    def stop(self):
    	print "STOPPING"
        self.circuit.trigger(2)
        zeros = numpy.zeros(self.maxBufferSize)
        self.circuit.sig.WriteTagV(0, zeros)
        
    
class DSPInterface:
    def __init__(self, waveGenerator, uploadBlockSize, minBufferSize=None):
        self.waveGenerator = waveGenerator
        self.uploadBlockSize = uploadBlockSize
        self.minBufferSize = uploadBlockSize if minBufferSize == None else minBufferSize
        self.dsp = equipment.dsp()
        self.circuit = self.dsp.load('RepeatPlayRecord','RX6')
        self.samplingFrequency = self.circuit.fs
        self.maxBufferSize = self.circuit.sig_n.value
        #self.circuit.play_dur_n.set(1, src_unit='s')
        self.circuit.start()
        self.waveGenerator.reset()
        self.waveGenerator.setSamplingFrequency(self.samplingFrequency)
        self.waveGenerator.setSamplingSize(self.uploadBlockSize)
        self.listener = Listener.Listener(self.uploadNextBlock, self.checkForNextUpload, 0.1)
        self.filledBufferPosition = 0
        self.uploadNextBlock()
        
    def checkForNextUpload(self):
        circuitBufferPosition = self.circuit.sig_idx.value
        print circuitBufferPosition
        filledBufferPosition = self.filledBufferPosition
        if circuitBufferPosition > self.filledBufferPosition: #Then we assume that the filled Buffer has wrapped around the DSP, but the sound being played has yet to wrap around the buffer
            filledBufferPosition += self.maxBufferSize
        if filledBufferPosition - circuitBufferPosition <= self.minBufferSize:
            return True
        return False
        
    def uploadNextBlock(self):
        upload = self.waveGenerator.next()
        if len(upload) + self.filledBufferPosition < self.maxBufferSize:
            self.uploadData(upload)
            self.filledBufferPosition += len(upload)
        else:
            self.uploadData(upload[:self.maxBufferSize - self.filledBufferPosition])
            self.uploadData(upload[self.maxBufferSize - self.filledBufferPosition:], pos = 0)
            self.filledBufferPosition += len(upload) - (self.maxBufferSize - self.filledBufferPosition)

    def uploadData(self, dataToUpload, pos=None, segmentSize=1000):
        currentIndex = 0
        if pos != None:
            #print pos, currentIndex, segmentSize
            self.circuit.sig.WriteTagV(pos, dataToUpload[currentIndex:currentIndex+segmentSize])
            currentIndex += segmentSize
        while currentIndex < len(dataToUpload):
        	#print dataToUpload[currentIndex:currentIndex+segmentSize]
            self.circuit.sig.write(dataToUpload[currentIndex:currentIndex+segmentSize])
            currentIndex += segmentSize
            #wxPython.yield() #So for long upload times, the GUI still interacts with the user
        print  'uploading', len(dataToUpload)
            
    def start(self):
        self.listener.start()
        #self.circuit.start()
        print "Trigger:",self.circuit.trigger(1)
    
    def stop(self):
        self.listener.stop()
        self.circuit.trigger(2)
        self.circuit.stop()
