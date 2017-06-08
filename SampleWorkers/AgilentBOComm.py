'''
    MG: 2014-07-20
    Communication class for Agilent N6700B, To control the B-field and oven on the X88 experiment.
    Type: N6700B allows for direct TCP socket communication. See programmers manual for details.
    
    The output sent from the server is contained in self.internal_state Who's format is e.g.
    
    STATUS 1407968999.12 {'BNormState': False, 'BPerpCurrentOP': 0.0001481553, 'OvenVoltageOP': 0.001234888, 'BPerpCurrentLim': 1.5, 'OvenVoltageLim': 0.02, 'BNormChannel': 2, 'OvenState': False, 'BPerpState': False, 'BNormVoltageOP': 0.001631606, 'OvenCurrentOP': -5.281001e-05, 'BAxialCurrentLim': 1.9, 'BAxialState': True, 'BNormVoltageLim': 0.04, 'OvenCurrentLim': 0.08, 'BAxialVoltageLim': 2.0, 'BPerpChannel': 3, 'BNormCurrentOP': -0.0006536378, 'BNormCurrentLim': 0.08, 'BAxialChannel': 1, 'BPerpVoltageLim': 2.0, 'BAxialVoltageOP': 1.295337, 'BAxialCurrentOP': 1.899982, 'BPerpVoltageOP': -0.0006340395, 'OvenChannel': 4}
    
    Available set methods can be found in METHODSAVAILABLE, also callable from the server.
    
    units are in Amps [A] and Volts [V]
    
    
'''


import socket
import time
import sys
import os
import numpy as np
import string

#Define global variables
DEBUG = False
DEVICELOC = "NAME"
PORT = 0000

class Comm:
    def __init__(self):  
        try:
            
            #Connect to device
            self.hostname = socket.gethostbyname(DEVICELOC)
            self.host     = socket.gethostbyname(self.hostname) 
            self.soc      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.soc.settimeout(0.5)
            self.soc.connect((self.host, PORT))
            

            
            #Channel state, format [OUtput state,Current limit, Voltage limit, Current output, Voltage output]
            self.channels = ["BAxial","BNorm", "BPerp","Oven"]
            self.parameters = ["State", "CurrentLim","VoltageLim","CurrentOP", "VoltageOP"]
            self.internal_state = {}
            self.internal_state["OvenChannel"] = 4
            self.internal_state["OvenState"] = False
            self.internal_state["OvenCurrentLim"] = 0
            self.internal_state["OvenVoltageLim"] = 0
            self.internal_state["OvenCurrentOP"]  = 0
            self.internal_state["OvenVoltageOP"]  = 0

            self.internal_state["BAxialChannel"] = 1
            self.internal_state["BAxialState"] = False
            self.internal_state["BAxialCurrentLim"] = 0
            self.internal_state["BAxialVoltageLim"] = 0
            self.internal_state["BAxialCurrentOP"]  = 0
            self.internal_state["BAxialVoltageOP"]  = 0

            self.internal_state["BNormChannel"] = 2
            self.internal_state["BNormState"] = False
            self.internal_state["BNormCurrentLim"] = 0
            self.internal_state["BNormVoltageLim"] = 0
            self.internal_state["BNormCurrentOP"]  = 0
            self.internal_state["BNormVoltageOP"]  = 0

            self.internal_state["BPerpChannel"] = 3
            self.internal_state["BPerpState"]   = False
            self.internal_state["BPerpCurrentLim"] = 0
            self.internal_state["BPerpVoltageLim"] = 0
            self.internal_state["BPerpCurrentOP"]  = 0
            self.internal_state["BPerpVoltageOP"]  = 0
            
            
            print 'Connected to device: %s'%(self.get_name())
            time.sleep(0.1)
            self.UPDATE()
            
        except Exception as e:
            print 'Failed opening socket, Check device connection: ',e
            sys.exit(1)
    def get_name(self):
        '''
            Function for obtaining the device ID
            returns something like:Agilent Technologies,N6700B,MY54000348,D.02.01
            For debugging purposes only, not used in internal_state
        '''
        msg = "*IDN?\n"
        
        self.soc.sendall(msg)
        time.sleep(0.1)
        rv = self.soc.recv(1024)
        
        return rv
                    
    def UPDATE(self):
        '''
            Function gets the current device state, output on/off (True/False) of each channel,
            current limit, voltage limit, current output, and voltage output for each channel.
            It then updates the internal_state variable and returns.
            For further optimization one could consider breaking this update into sub-updates, but 
            as is this only takes ~50ms
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error 
        '''
        try:
            msgs = ["OUTP? (@1,2,3,4)\n",
                    "SOUR:CURR? (@1,2,3,4)\n",
                    "MEAS:CURR:DC? (@1,2,3,4)\n",
                    "SOUR:VOLT? (@1,2,3,4)\n",
                    "MEAS:VOLT:DC? (@1,2,3,4)\n"]
            
            recvmsg = []
            for i in msgs:
                self.soc.sendall(i)
                recv = string.split(self.soc.recv(1024),'\n')[0]
                if DEBUG: print recv
                recvmsg.append(string.split(recv,',') )
                
            for i in range(0,4):
                self.internal_state["%s%s"%(self.channels[i],self.parameters[0])] = bool(int(recvmsg[0][i]))
                self.internal_state["%s%s"%(self.channels[i],self.parameters[1])] = float(recvmsg[1][i])
                self.internal_state["%s%s"%(self.channels[i],self.parameters[2])] = float(recvmsg[3][i])
                self.internal_state["%s%s"%(self.channels[i],self.parameters[3])] = float(recvmsg[2][i])
                self.internal_state["%s%s"%(self.channels[i],self.parameters[4])] = float(recvmsg[4][i])

            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1
            
    def STOP(self):
        '''
            closes socket
        '''
        self.soc.close()

    def CURRENT(self,channel,value):
        '''
            Sets the current on channel [channel] to the value [value] in amps.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:CURR:LEV %.5f,(@%i)\n"%(float(value),int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error setting current: ",e
        return 0
    
    def VOLTAGE(self,channel,value):
        '''
            Sets the voltage on channel [channel] to the value [value] in volts.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:VOLT:LEV %.5f,(@%i)\n"%(float(value),int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error in setting voltage: ",e
            
    def ON(self,channel):
        '''
            Turns on channel [channel]
            inputs: channel [int]
            returns: 0
        '''
        try:
            msg = "OUTP ON,(@%i)\n"%(int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error turning on channel: ",e
    
    def OFF(self,channel):
        '''
            Turns off channel [channel]
            inputs: channel [int]
            returns: 0
        '''
        try:
            msg = "OUTP OFF,(@%i)\n"%(int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error turning on channel: ",e
        
    '''        
    Functions intended to be called from webDAQ
    '''           
    def BAxialCurrentLim(self,value):
        self.CURRENT(1,value)
        
    def BAxialVoltageLim(self,value):
        self.VOLTAGE(1,value)
        
    def BAxialState(self, value):
        if value == 'ON' or value == True:
            self.ON(1)
        elif value == 'OFF' or value == False:
            self.OFF(1)
        else:
            print 'Error in received value'
                
        
    def BNormCurrentLim(self,value):
        self.CURRENT(2,value)
        
    def BNormVoltageLim(self,value):
        self.VOLTAGE(2,value)
        
    def BNormState(self,value):
        if value == 'ON' or value == True:
            self.ON(2)
        elif value == 'OFF' or value == False:
            self.OFF(2)
        else:
            print 'Error in received value'
            
    def BPerpCurrentLim(self,value):
        self.CURRENT(3,value)
        
    def BPerpVoltageLim(self,value):
        self.VOLTAGE(3,value)
        
    def BPerpState(self,value):
        if value == 'ON' or value == True:
            self.ON(3)
        elif value == 'OFF' or value == False:
            self.OFF(3)
        else:
            print 'Error in received value' 


    def OvenCurrentLim(self,value):
        if float(value) < 3.0:
            self.CURRENT(4,value)
        else:
            print 'WARNING: DO NOT RUN OVEN @ > 3.0A'
        
    def OvenVoltageLim(self,value):
        self.VOLTAGE(4,value)
        
    '''        
    def OvenState(self, value):
        if value == 'ON' or value == True:
            self.ON(4)
        elif value == 'OFF' or value == False:
            self.OFF(4)
        else:
            print 'Error in received value'
    '''        
    
    def OvenState(self,value):
        '''
            Ramps channel to the set value
        '''
        try:
            if value =='ON' or value == True:
                rampval = np.linspace(0.0, self.internal_state["OvenCurrentLim"],10)
                msg = "SOUR:CURR:LEV %.5f,(@%i)\n"%(float(0.0),int(4))
                if DEBUG: print msg
                self.soc.sendall(msg)

                self.ON(4)
                for i in rampval:
                    msg = "SOUR:CURR:LEV %.5f,(@%i)\n"%(float(i),int(4))
                    if DEBUG: print msg
                    self.soc.sendall(msg)
                    time.sleep(0.01)
                    self.UPDATE()
            elif value == 'OFF' or value == False:
                self.OFF(4)
        except Exception as e:
            print "Error in ramping channel %i"%(int(4))
            print e                   
        

    def METHODSAVAILABLE(self):
        availmeth = []
        for i in self.channels:
            availmeth += ['%sCurrentLim'%(i),'%sVoltageLim'%(i),'%sState'%(i)]
       
        return availmeth
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
