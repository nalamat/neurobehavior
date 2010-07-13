import threading, time

class Listener(threading.Thread):
    def __init__(self, funcToCall, triggerFunc, secondsBetweenChecks):
        threading.Thread.__init__(self)
        self.funcToCall = funcToCall
        self.triggerFunc = triggerFunc
        self.secondsBetweenChecks = secondsBetweenChecks
        self.end = False
    def run(self):
        while not self.end:
            if self.triggerFunc():
                self.funcToCall()
            time.sleep(self.secondsBetweenChecks)
        self.end = False
    def stop(self):
        self.end = True

if __name__=='__main__':
    class foo:
        def __init__(self):
            self.ctrlVar = 0
        def check(self):
            return self.ctrlVar > 10
        def reset(self):
            self.ctrlVar = 0
    f = foo()
    l = ActiveListener(f.reset, f.check, 0.5)
    l.start()
    try:
        while True:
            f.ctrlVar += 1
            print f.ctrlVar
            time.sleep(0.1)
    except:
        l.stop()
    
