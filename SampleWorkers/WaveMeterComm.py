# MTserver version of High-finesse Ws7 wavemeter

            
import sys, os, time, socket, threading, ctypes, traceback
from ctypes import *

DEBUG=False

class Comm:
    def __init__(self):  
        try:

            self.internal_state = {}
            self.internal_state["WaveMeterChannel1"] = 0.0
            self.internal_state["WaveMeterChannel2"] = 0.0
            self.internal_state["WaveMeterChannel3"] = 0.0
            self.internal_state["WaveMeterChannel4"] = 0.0
            self.internal_state["WaveMeterChannel5"] = 0.0
            self.internal_state["WaveMeterChannel6"] = 0.0
            self.internal_state["WaveMeterChannel7"] = 0.0
            self.internal_state["WaveMeterChannel8"] = 0.0
            
            
            self.wd = ctypes.WinDLL("wlmData")
            x = self.wd.Instantiate(0,0,0,0)
            self.wd.GetFrequencyNum.restype = c_double
            self.wd.GetFrequencyNum.argtypes = [c_int,c_double]
            
        except Exception as e:
            print 'Initialization failed: ' + str(e)
            print traceback.format_exc()
            sys.exit(1)

    def UPDATE(self):
        try:

            for k in range(1,9):
                self.internal_state["WaveMeterChannel" + str(k)] = self.wd.GetFrequencyNum(k, 0)
                    
            if DEBUG: print self.internal_state
            return self.internal_state
            
        except Exception as e:
            print "Error: " + str(e)
            print traceback.format_exc()


