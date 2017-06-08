'''
    Michael Gutierrez: 2015-03-18
    Communication class for Agilent 33220A

    Available set methods can be found in METHODSAVAILABLE, also callable from the server.

    units are in megahertz [Hz] and millivolts [V]


'''


import time
import sys
import serial
import os
import numpy as np
import string

#Define global variables
DEBUG = False
DEVICELOC = 'NAME'


class Comm:
    def __init__(self):
        try:
            
            self.dev = os.open(DEVICELOC, os.O_RDWR)
            os.write(self.dev, 'SYST:REM\n') #put into remote mode
            os.write(self.dev, '*CLS\n') # clear error queue
            
            self.internal_state = {}

            time.sleep(0.1)
            self.GetState()

        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            sys.exit(1)


    def UPDATE(self):
        pass

    def GetState(self):
        '''
            Function gets the current device state, output frequency and amplitude
            It then updates the internal_state variable and returns.
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error
        '''
        try:
            meascommand = 'FUNCtion?\n'
            self.serial.write(meascommand)
            time.sleep(0.05)
            self.internal_state["Mode"] = self.serial.read(1000).rstrip()
            
            
            meascommand = 'FREQ?\n'
            self.serial.write(meascommand)      #asks for frequency
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["Frequency"] = int(float(self.serial.read(1000).rstrip())/1000000.0)

            meascommand = 'VOLT?\n'
            self.serial.write(meascommand)      #asks for voltage amplitude
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["Amplitude"] = float(self.serial.read(1000).rstrip())*1000.0
            
            
            meascommand = 'VOLTage:OFFset?\n'
            self.serial.write(meascommand)
            self.sleep(0.05)
            self.internal_state['Offset'] = float(self.serial.read(1000).rstrip())
            
            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1

    def STOP(self):
        '''
            closes serial communication
        '''
        os.close(self.dev)

    def Mode(self,mode):
        '''
            Checks what mode the function generator is in. e.g. DC, Sine, Ramp, square etc.
        '''
        try:
            msg = 'FUNCtion %s\n'%(str(mode))
            if not mode == 'SIN' or mode == 'SQU' or mode == 'RAMP' or mode == 'DC'
                if DEBUG : print msg
            
                os.write(self.dev, msg)
                self.internal_state["Mode"] = mode
            else: raise
        except Exception as e:
            print 'Error in setting mode: ',e
        
        
    def Frequency(self,value):
        '''
            Sets the frequency to the value [value] in hertz.
            inputs: value [float]
            returns: 0
        '''
        if value <= 0:
            print "Error, invalid frequency"
            return 0
        try:
            freq = int(float(value)*1000000.0)
            msg = 'FREQ '+'%d'%(freq)+'\n'
            if DEBUG : print msg

            os.write(self.dev, msg)
            time.sleep(0.01) #Time for command to be read in
            self.internal_state["Frequency"] = freq
        except Exception as e:
            print "Error setting current: ",e
        return 0

    def Amplitude(self,value):
        '''
            Sets the amplitude to the value [value] in volts.
            inputs: value [float]
            returns: 0
        '''
        try:
            amp = float(value)
            msg = 'VOLT '+'%.4f'%(amp)+'\n'
            if DEBUG: print msg

            self.serial.write(msg)
            time.sleep(0.01) #Time for command to be read in
            self.internal_state["Amplitude"] = amp
        except Exception as e:
            print "Error in setting voltage: ",e

    def Offset(self,value):
        '''
            sets the offset to the value [value] in volts
            inputs: value [float]
            return: 0
        '''
        if abs(value) < 5
    
    
    def METHODSAVAILABLE(self):
        return ['Mode','Frequency','Amplitude']
