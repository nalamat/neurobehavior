import WaveGenerator
#import sys
#sys.path.append('cns/')
import DSPInterface
import time
if __name__ == '__main__':
    wave = WaveGenerator.WaveGenerator()
    #simpleDsp = DSPInterface.SimpleDSPInterface(wave)
    #simpleDsp.start()
    #time.sleep(2)
    #print 'success'
    #simpleDsp.stop()
    dsp = DSPInterface.DSPInterface(wave, 90000, minBufferSize=180000)
    dsp.start()
    try:
        while True:
            time.sleep(2)
    except:
        pass
    dsp.stop()
