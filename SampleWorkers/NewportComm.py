# Communications module for Newport 6700 Laser Controller
# By Tessa Green


#import serial #use pyserial on windows if needed
import time
import sys
import os
import socket
import threading
import ctypes
import string

from ctypes import *
wd=ctypes.WinDLL("usbdll")
#usbdll.dll must be in the same folder as this file.


DEBUG=False

#notes on commands:
#    DO NOT ADJUST TEMPERATURE
#    DO NOT SENT CURRENT >165 mA
#    DO NOT RAPIDLY/REPEATEDLY TURN LASER ON AND OFF


#notes on troubleshooting:
#    Giving further commands while the laser adjusts to being
#    turned on/off can cause faulty responses. A time.sleep(30) 
#    command has been added to the function ON(). If there is an 
#    issue with multiple computers/the problem re-emerges, consider
#    adding a similar time.sleep to OFF()
#
#    Operating from the command line while the New Focus Tunable Laser Application
#    is open will cause faulty returns.
#




class newportError:
    def __init__(self, value):
        self.value=value
    def __str__(self):
        return repr(self.value)

#if you want to enter remote mode:
    #disables the knobs
    #call "SYSTem:MCONtrol REM"
    #exit by calling "SYST:MCON LOC"
    #also disable by turning the power on and off
    


class Comm:
 
    def __init__(self):#,sn):
        '''
            Initializes command class. 
            input: integer laser serial number, already added to key_dict
        '''
        try:
            # initialize all devices
            testnum=wd.newp_usb_init_product(c_int(0))           
            testnum=wd.newp_usb_open_devices(c_int(0),c_bool(False),ctypes.create_string_buffer(64))
            
            #if testnum !=0: raise newportError("init")
            szDevInfo=ctypes.create_string_buffer(1024)
            testnum=wd.newp_usb_get_device_info(szDevInfo)
            #if testnum !=0: raise newportError("info")
            print "Looking for devices"
            print szDevInfo.value

            #wd.GetInstrumentList()



            '''
            response=ctypes.create_string_buffer(64)

            thing=c_ulong(0)
            pthing=pointer(thing)
            testnum=wd.newp_usb_write_by_key(ctypes.create_string_buffer("TLB-6700-LN SN1147"),ctypes.create_string_buffer("*IDN?\r\n"),c_ulong(len("*IDN?\r\n")))
            
            if DEBUG: print "newp_usb_write_by_key: "+str(testnum)+"\n"
            if testnum !=0: raise newportError("write")
            
            #contacts laser again for response
            #the value of c_ulong(64) must match the size of the response 
            #string buffer created above.
            testnum=wd.newp_usb_read_by_key(ctypes.create_string_buffer("TLB-6700-LN SN1147"),response,c_ulong(64),pthing)
            
            if DEBUG: print "newp_usb_read_by_key: "+str(testnum)+"\n"
            if testnum !=0: raise newportError("read")

            print response.value.split("\r\n")[0]

            testnum=wd.newp_usb_write_by_key(ctypes.create_string_buffer("6700 SN10066"),ctypes.create_string_buffer("*IDN?\r\n"),c_ulong(len("*IDN?\r\n")))
            
            if DEBUG: print "newp_usb_write_by_key: "+str(testnum)+"\n"
            if testnum !=0: raise newportError("write")
            
            #contacts laser again for response
            #the value of c_ulong(64) must match the size of the response 
            #string buffer created above.
            testnum=wd.newp_usb_read_by_key(ctypes.create_string_buffer("6700 SN10066"),response,c_ulong(64),pthing)
            
            if DEBUG: print "newp_usb_read_by_key: "+str(testnum)+"\n"
            if testnum !=0: raise newportError("read")

            print response.value.split("\r\n")[0]
            '''

            #false boolean means that other commands are called
            #using the device key as the device ID
            #Device key: "TLB-6700-LN SN1147" or similar
            if DEBUG: print "newp_usb_open_devices: "+str(testnum)+"\n"
            if testnum !=0:
                raise newportError("wd.newp_usb_open_devices error")
            
            #dictionary of relevant serial key formats.
            #Different TLB-6700 lasers have, for no apparent reason
            #differently formatted keys. New lasers should be manually
            #added below.
            #Keys can be found by opening the Tunable Laser Application to
            #the "Discovery" tab, where a list of discovered devices is shown.
            #Alternately, the function queryDevices() in this script can be run.
            #self.key_dict=dict()
            #self.key_dict[1147]="TLB-6700-LN SN1147"
            #self.key_dict[10066]="6700 SN10066"
            

            self.lasers={'461','1033','844TA'}

            
            
            #initializes tracked/updated variables and command dictionary
            #can add/delete queries here as needed
            self.vars={}
            self.vars['461']={"SOUR:VOLT:PIEZ?":"PiezoVoltage461","SENS:CURR:DIOD":"DiodeCurrent461","OUTP:STAT?":"OutputState461"}
            self.vars['1033']={"SOUR:VOLT:PIEZ?":"PiezoVoltage1033","SENS:CURR:DIOD":"DiodeCurrent1033","OUTP:STAT?":"OutputState1033"}
            self.vars['844TA']={"SOUR:CPOWER?":"OutputMode844TA","SENS:POW:DIOD?":"OutputPower844TA","SOUR:POW:DIOD?":"SetOutputPower844TA","SENS:POW:INPUT?":"InputPower844TA","OUTP:STAT?":"OutputState844TA"}

            #self.internal_state=dict((self.vars[f],True) for f in self.vars)
            self.internal_state={}
            self.internal_state["PiezoVoltage461"]=0
            self.internal_state["PiezoVoltage1033"]=0
            self.internal_state["DiodeCurrent461"]=0
            self.internal_state["DiodeCurrent1033"]=0
            self.internal_state["OutputPower844TA"]=0
            self.internal_state["InputPower844TA"]=0
            self.internal_state["OutputState844TA"]=0
            #if (sn in self.key_dict)==False:
            #    print "Please give a valid integer serial number."
            #    print "Added lab lasers include: "+str(self.key_dict.keys())
            #    raise newportError(0)
            self.device_key={}
            self.device_key['461']="TLB-6700-LN SN1147"
            self.device_key['1033']="6700 SN10066"
            self.device_key['844TA']="TA-7600-LN 10012"
            #updates values of internal state variables
            time.sleep(5)
            self.update_internal_state()
            
        except newportError as e:
            print "Could not initialize Newport devices\n"
            sys.exit(1)
            #do not pass because if can't initialize can't do anything
    
    def send_command(self,command,laser):
        '''
            Sends a pre-formatted command to the laser
            and returns its response.
            input: command (string)
            output: response (string)
        '''
        try:

            if DEBUG: print "sending command: ",command,"\n"
            #response holds the final output
            response=ctypes.create_string_buffer(64)
            #newline and carriage return must be added to read/write by key
            command=command+"\r\n"
            
            thing=c_ulong(0)
            pthing=pointer(thing)
            #this will hold the number of bytes sent 
            #I think. Should check this is Newpdll.h
            
            #sends command to the laser
            #function documentation in Newpdll.h
            #print self.device_key[laser]
            testnum=wd.newp_usb_write_by_key(ctypes.create_string_buffer(self.device_key[laser]),ctypes.create_string_buffer(command),c_ulong(len(command)))
            
            if DEBUG: print "newp_usb_write_by_key: "+str(testnum)+"\n"
            if testnum !=0: raise newportError("write")
            time.sleep(0.1)
            
            
            #contacts laser again for response
            #the value of c_ulong(64) must match the size of the response 
            #string buffer created above.
            testnum=wd.newp_usb_read_by_key(ctypes.create_string_buffer(self.device_key[laser]),response,c_ulong(64),pthing)
            print response.value.split("\r\n")[0]
            if DEBUG: print "newp_usb_read_by_key: "+str(testnum)+"\n"
            if testnum !=0: raise newportError("read")

            return response.value.split("\r\n")[0]
            
        except newportError as e:
            if e.value == "write":
                print "Unable to send the command\n"
                #pass
            elif e.value == "read":
                print "Command sent but response not able to be read\n"
                #pass
            else:
                "command/response error: ",e,"\n"
            raise newportError("send_command")
            pass
            #not certain I'm doing this bit properly?
            
    def update_internal_state(self):
        '''
            Calls update_var for each variable being 
            tracked/updated in the internal state dictionary.
            input: none
            return: none
        '''
        
        try:
            print "updating internal state"
            if DEBUG: print "updating internal state\n"
            #update each variable individually
            #makes it easier to add additional variable later
            for var in self.vars['461']:
                self.internal_state[self.vars['461'][var]]=self.send_command(var, '461')
            for var in self.vars['1033']:
                self.internal_state[self.vars['1033'][var]]=self.send_command(var,'1033')
            for var in self.vars['844TA']:
                self.internal_state[self.vars['844TA'][var]]=self.send_command(var,'844TA')
            print self.internal_state
        except newportError as e:
            print 'Failed in update_internal_state: ',e,"\n"
            pass
    
    def update_var(self,var):
        '''
            Updates the status of a variable in
            the dictionary self.internal_state.
            input: the query command returning the desired value
            output: none.
        '''
        try:
            if DEBUG: print "updating variable: "+var+"\n"
            value=self.send_command(var)
        except newportError as e:
            print "error in: "+e.value+"\n"
            print "Could not update variable: "+var+"\n"
            raise newportError(var)
            pass
        else:
            if DEBUG: print var+" returns "+value+"\n"
            self.internal_state[self.vars[var]]=value


    
    def error_check(self):
        '''
            Checks if the laser error buffer is full.
            If it is full, prints its contents and empties it.
            import: none
            return: none
        '''
        try: 
            stb=self.send_command("*STB?")
            
            if stb=="128": #the error buffer is full
                #outputs the contents of the buffer
                print self.send_command("ERRSTR?")
            elif stb =="0":
                if DEBUG: print "Error buffer empty"
                #maybe do this all the time, not just at debug?
            else:
                raise newportError("0")
        except newportError as e:
            print "Unable to complete error buffer check\n"
            pass
    
    def ON(self, laser):
        '''
            Turns on the laser.
            inputs: none
            returns: none
        '''
        try:
            if DEBUG: print "Turning on the laser"
            check=self.send_command("OUTPUT:STATE ON", laser)
            if DEBUG: print "response: "+check+"\n"
            if check!="OK":
                raise newportError("power")
            
        except newportError as e:
            print "Could not turn on laser:"
            if e.value == "send_command":
                print "Command could not be sent\n"
            elif e.value == "power":
                print "Power command did not return OK"
                self.error_check()
            pass
        else:
            time.sleep(30) 
            #wait until laser is fully powered on before
            #sending any further commands.
            #Not waiting long enough causes program crashes
        
    def OFF(self):
        '''
            Turns off the laser.
            inputs: none
            outputs: none
        '''
        try:
            if DEBUG: print "Turning off the laser"
            check=self.send_command("OUTPUT:STATE OFF")
            if DEBUG: print "response: "+check+"\n"
            if check !="OK": raise newportError("power")
            
        except newportError as e:
            print "Could not turn off laser:"
            if e.value == "send_command":
                print "Command could not be sent\n"
            elif e.value == "power":
                print "Power command did not return OK"
                self.error_check()
            pass    

    def SET_PIEZO(self,percent,laser):
        '''
            Sets the voltage on the piezo to 
            the percentage given.
            input: percent, a number between 0 and 100
            returns: none
        '''
        try: 
            if DEBUG: print "Setting piezo value to: "+str(percent)+"\n"
            sender="SOUR:VOLT:PIEZ"+" "+str(percent)
            check=self.send_command(sender,laser)
            if check != "OK":
                raise newportError("piezo")
            self.internal_state["PiezoVoltage" + laser]=float(percent)
        except newportError as e:
            print "Could not set piezo value:"
            if e.value == "send_command":
                print "Command could not be sent\n"
            elif e.value == "piezo":
                print "Set piezo command did not return OK"
                self.error_check()
            pass

            
    def SET_DIODE(self,value,laser):
        '''
            Sets the laser diode current.
            input: value
                if value is the string "MAX", the current set point is 
                set to the diode rating.
                Otherwise, value may be a float specifying current in mA
            return: none
        '''
        try:
            if DEBUG: print "Setting diode current to: "+str(value)+"\n"
            sender="SOUR:CURR:DIOD"+" "+str(value)
            if value == "MAX": value=164.9
            
            if float(value)>165:
                raise newportError("range")
            else: 
                check=self.send_command(sender, laser)
                
            if check == "VALUE OUT OF RANGE":
                raise newportError("range")
            elif check != "OK":
                raise newportError("current")
            self.internal_state["DiodeCurrent" + laser]=float(percent)
        except newportError as e:
            print "Could not set the diode current:"
            if e.value == "send_command":
                print "Command could not be sent\n"
            elif e.value == "range":
                print "Current value was out of range"
                print "Diode current should be <165 mA"
            elif e.value == "current":
                print "Diode current set command did not return OK"
                self.error_check()
            pass
    
    def UPDATE(self):
        '''
            Updates all internal state variables in self.vars 
            and returns them in a string array [".",".",...]
        '''
        try:
            #if DEBUG: print "Updating internal_state..."
            self.update_internal_state()
            return self.internal_state
        except Exception as e:
            print "Failed in Update: ",e
            pass

    def STATUS(self,query):
        '''
            Reads the current internal state of the associated query.
            input: query (string)
            return: string, "-1" in error case.
        '''
        try:
            if DEBUG: print "Getting current status of "+query
            #self.update_var(query)
            #uncomment the above line to also update the value
            return self.internal_state[query]
        except newportError as e:
            print 'Failed in STATUS: ',e
            return "-1"
            pass
    
    def STOP(self):
        '''
            closes communication with USB devices
        '''
        try:
            if DEBUG: print "Closing communication with USB devices"
            testnum=wd.newp_usb_uninit_system()
            if testnum != 0:
                raise newportError(0)
            
        except newportError as e:
            print "Unable to close communication"

    def DiodeCurrent1033(self, value):
        self.SET_DIODE(value, '1033')
    def DiodeCurrent461(self, value):
        self.SET_DIODE(value, '461')        
    def OutputState461(self, value):
        if value == 'ON' or value == True:
            self.ON('461')
        elif value == 'OFF' or value == False:
            self.OFF('461')
        else:
            print 'Error in received value: OutputState=%s' (str(value))
    def OutputState1033(self, value):
        if value == 'ON' or value == True:
            self.ON('1033')
        elif value == 'OFF' or value == False:
            self.OFF('1033')
        else:
            print 'Error in received value: OutputState=%s' (str(value))
    def OutputState844TA(self, value):
        if value == 'ON' or value == True:
            self.ON('844TA')
        elif value == 'OFF' or value == False:
            self.OFF('844TA')
        else:
            print 'Error in received value: OutputState=%s' (str(value))
    def PiezoVoltage1033(self, value):
        value=float(value)
        if value >= 0 and value <= 100 and abs(value-float(self.internal_state['PiezoVoltage1033']))<0.1:
            self.SET_PIEZO(value, '1033')
        else:
            print 'Error in received value: PiezoVoltage=%s' (str(value))
    def PiezoVoltage461(self, value):
        value=float(value)
        if value >= 0 and value <= 100 and abs(value-float(self.internal_state['PiezoVoltage461']))<0.1:
            self.SET_PIEZO(value, '461')
        else:
            print 'Error in received value: PiezoVoltage=%s' (str(value))
    def SetOutputPower844TA(self,value):
        value=float(value)
        try: 
            if DEBUG: print "Setting output power value to: "+str(percent)+"\n"
            sender="SOUR:POW:DIOD"+" "+str(percent)
            check=self.send_command(sender,laser)
            if check != "OK":
                raise newportError("power")
            self.internal_state["OutputPower844TA"]=float(percent)
        except newportError as e:
            print "Could not set power value:"
            if e.value == "send_command":
                print "Command could not be sent\n"
            elif e.value == "power":
                print "Set power command did not return OK"
                self.error_check()
            pass