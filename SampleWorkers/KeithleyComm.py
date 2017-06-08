'''
    Michael Gutierrez: 2015-03-22
    Communication class for Agilent 34401A, To read the ULE cavity temperature.

    units are in volts [V] and degrees C [C]


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

            #Open Serial Connection with device
            serial_settings={"port":DEVICELOC,"baudrate":9600, "timeout":.5,"rtscts":True,}
            self.serial=serial.Serial(**serial_settings)
            self.serial.write('SYST:REM\n')
            self.serial.write('*CLS\n')
            self.serial.read()

            self.internal_state = {}
            self.internal_state["Volt"] = 2.0
            self.internal_state["Red_Temp"] = 0
            time.sleep(0.1)
            self.UPDATE()
            
            self.internal_state["temp_setvoltage"]=self.internal_state["Volt"]
        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            sys.exit(1)
    
    def TempConversion(V):
            '''
            Converts a voltage measurement to a temperature in celsius. 
            
            wavelength electronics controller uses 100uA to measure, conversion from
            resistance to voltage done through wavelength electronics function
            for 20k thermister
            '''
            Acoeff = 9.6542E-04
            Bcoeff = 2.3356E-04
            Ccoeff = 7.7781E-08
            Rmeas = V/(100E-06)
            return 1/( Acoeff + Bcoeff*np.log(Rmeas) + Ccoeff*(np.log(Rmeas))**3 )
        
    
    def UPDATE(self):
        '''
            measures the current set point.
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error
        '''
        try:
            meascommand = 'MEASure?\n'
            self.serial.write(meascommand)      #asks for frequency
            time.sleep(0.05) #time for device to load buffer
            setpoint=float(self.serial.read(24).rstrip().rsplit(',')[0])
            self.internal_state["Volt"] = setpoint
            self.internal_state["Red_Temp"] = TempConversion(setpoint)
            print self.internal_state
            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1
    
    def SetVoltage(self,voltage):
        '''
            Loads a set voltage into memory, will not set the device 
            until confirmation is given
        '''
        self.internal_state['temp_setvoltage']=float(voltage)
        
        
    def ConfirmsetVoltage(self,state):
        '''
        
        '''
        if state == True:
            msg = ':SOUR:VOLT:LEV %f\n'%(self.internal_state['temp_setvoltage'])
        else:
            print 'No update requested'
        
        self.serial.write(msg)
        time.sleep(0.01)
        self.UPDATE()
        
    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()


    def METHODSAVAILABLE(self):
        return []
