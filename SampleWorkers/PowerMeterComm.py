'''
    HZ: 2014-08-29
    Communication class for Thorlabs power meters
   
'''


import serial
import time
import sys
import os
import string
import usbtmc

#Define global variables
DEBUG = False
DEVICENAME = 'NAME'

class Comm:
    def __init__(self):
        
        try:
            #self.FILE = os.open(DEVICENAME, os.O_RDWR)  
            self.FILE = usbtmc.Instrument(0x1313, 0x8078)
            #os.write(self.FILE,'*CLS\n')
            self.FILE.write('*CLS\n')
            #.write(self.FILE,'*CLS\n') #clears errors and device buffer
            self.internal_state = {'PowerMeterWavelength': 0.0, 'PowerMeterPower': 0.0, 'PowerMeterMinPower': 0.0, 'PowerMeterMaxPower': 0.0 }
            self.internal_state['PowerMeterWavelength'] = float(self.FILE.ask('CORR:WAV?\n'))
            #self.internal_state['PowerMeterMinPower'] = float(self.FILE.ask('CURR:RANG? MIN\n'))
            #self.internal_state['PowerMeterMaxPower'] = float(self.FILE.ask('CURR:RANG? MAX\n'))
        except Exception as e:
            print 'Could not initialize power meter',e
            sys.exit(1)
    
    def WAVELENGTH(self, wavelength):
        '''
            Sets the power meter wavelength to measure for
        '''
        try:
            # wavelength in nm
            cmd='CORR:WAV %f'%(float(wavelength)) 
            self.FILE.write(cmd)
            self.internal_state['PowerMeterWavelength']=float(wavelength)
        except Exception as e:
            print 'Failed in setting WAVELENGTH: ',e
            pass        
    		    
    def POWER(self):
        try:
            #os.write(self.FILE, 'READ?\n')
            #self.internal_state['Power']=float(os.read(self.FILE, 400))
            self.internal_state['PowerMeterPower']=float(self.FILE.ask('READ?\n'))*10**6
            self.internal_state['PowerMeterWavelength'] = float(self.FILE.ask('CORR:WAV?\n'))
            #self.internal_state['PowerMeterMinPower'] = float(self.FILE.ask('CURR:RANG? MIN\n'))
            #self.internal_state['PowerMeterMaxPower'] = float(self.FILE.ask('CURR:RANG? MAX\n'))
        except Exception as e:
            print 'Failed in reading POWER: ',e
            try:
                print 'trying to reconnect...'
                self.FILE.reset()
                print '...'
            except: pass
            pass 

    def UPDATE(self):
        '''
            Updates all internal state values 
            and returns them in a string array [".",".",...]
            
        '''
        try:
            if DEBUG: print 'Updating internal_state...'
            self.POWER()
            return str(self.internal_state)
        except Exception as e:
            print 'Failed in Update: ',e
            pass


            
    def STOP(self):            
        os.close(self.FILE)  
             
