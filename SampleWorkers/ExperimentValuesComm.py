'''
    MG: 2016-09-12

    Helpers for maintaining system settings through periodic calibration scripts. 
    Creates data file used by QuACK for periodic updates to system settings such as
    Rabi Pi-time, amplitude for pi-pulse, qubit AOM frequency, magnetic field, laser cooling settings etc
     
'''


import time
import datetime 
import sys
import os
import string
import yaml
import re
import ExperimentLogs.AtomicHelpers as AH
import numpy as np
import quackCon.simple_dds as simple_dds
import collections
import datetime

AtomicHelpers = AH.AtomicHelpers()
#Define global variables
DEBUG = False
ExpLogDir = os.environ['EXPVALUES'] +'/'
ExperimentValues = ExpLogDir + "CurrentValues.yaml"
ConstantsFILE = os.environ["QUACK"] + '/Constants.data'

mdict = {"12":1/2.,"32":3/2.,"52":5/2.,
         "-12":-1/2., "-32":-3/2.,"-52":-5/2.}

cheaderDict =collections.OrderedDict()
cheaderDict["Detection"] = collections.OrderedDict(
                           [("A_Z1detect_422"  ,"Z1Amp"         ),
                            ("F_Z1detect_422"  ,"Z1Freq"        ),
                            ("T_Z1detect"      ,"Z1Time"        ),
                            ("Z1Thresh1"       ,"Z1Threshold1"  ),
                            ("Z1Thresh2"       ,"Z1Threshold2"  ),
                            ("Z1Thresh3"       ,"Z1Threshold3"  ),
                            ("A_Z2detect_422"  ,"Z2Amp"         ),
                            ("F_Z2detect_422"  ,"Z2Freq"        ),
                            ("T_Z2detect"      ,"Z2Time"        ),
                            ("Z2Thresh1"       ,"Z2Threshold1"  ),
                            ("Z2Thresh2"       ,"Z2Threshold2"  ),
                            ("Z2Thresh3"       ,"Z2Threshold3"  )
                            ])
cheaderDict["DopplerCool"] = collections.OrderedDict(
                           [("A_Z1cool_422"  ,"Z1Amp"         ),
                            ("F_Z1cool_422"  ,"Z1Freq"        ),
                            ("A_Z2cool_422"  ,"Z2Amp"         ),
                            ("F_Z2cool_422"  ,"Z2Freq"        ),
                            ("T_cool"      ,"Time"        )
                            ])
cheaderDict["Transitions"] = collections.OrderedDict(
                             [  ("F_5Sn12_4Dn12","5S-12-4D-12"  ),
                                ("F_5Sn12_4Dn32","5S-12-4D-32"  ),
                                ("F_5Sn12_4Dn52","5S-12-4D-52"  ),
                                ("F_5Sn12_4D12" ,"5S-12-4D12"   ),
                                ("F_5Sn12_4D32" ,"5S-12-4D32"   ),
                                ("F_5S12_4Dn12" ,"5S12-4D-12"   ),
                                ("F_5S12_4Dn32" ,"5S12-4D-32"   ),
                                ("F_5S12_4D12"  ,"5S12-4D12"    ),
                                ("F_5S12_4D32"  ,"5S12-4D32"    ),
                                ("F_5S12_4D52"  ,"5S12-4D52"    ),
                                ("F_Carrier"    ,"Carrier"      ),
                                ("F_OPump"      ,"OpticalPumping")
                                ])
cheaderDict["StatePrep"] = {    "A_OPump":"Amp",
                                "T_OPump":"PiTime",
                                "OPLoops":"Loops"
}
cheaderDict["SBCool"] = {    "A_SB"     : "Amp",
                             "SBLoops"  : "Loops",
                             "T_SBzcom" : "PiTime-zcom",
                             "SBSequence":  ""}

cheaderDict["Carrier"] = {
                            "A_Carrier"  : "Z1Amp",
                            "T_Z1pi"     : "Z1PiTime",
                            "T_Z2pi"     : "Z2PiTime"

}

cheaderDict["MotionalFrequency"] ={
                            "F_SBzcom":"zcom",
                            "F_SBzstr":"zstr"
}

cheaderDict["SampleAndHold"] ={
                            "T_Hold":"Time",
                            "A_Hold":"Amp",
                            "DBHold":"DBHold"
}

def safely(f):
    def safe_f(*args,**kargs):
        try:
            name = f.__name__
        except:
            name = "unknown"
        try:
            return f(*args,**kargs)
        except Exception as e:
            print 'ERROR in %s: %s'%(name,e)
    return safe_f

class Comm:
    def __init__(self):
        try:
            with open(ExperimentValues, 'r') as f:
                self.internal_state = yaml.safe_load(f)
        except Exception as e:
            print 'Could load experiment constants',e
            sys.exit(1)
    

    @safely
    def UPDATE(self):
        if DEBUG: print self.internal_state
        self.drift_compensation()

    @safely
    def drift_compensation(self):
        #print 'Updating Drift...'
        timenow = float( datetime.datetime.utcnow().strftime('%s') )
        t = timenow-float(self.internal_state["Drift"]["Time1"])
        
        self.internal_state["Transitions"]["5S-4D"] += t*self.internal_state["Drift"]["RateHzps"]*1E-6
        self.internal_state["Drift"]["Time1"] = timenow
        self.CalcTransitionFrequencies()

    @safely         
    def LOAD(self, category, item, value):
        print '%s - %s : %s'%(category, item, value)
        if category in self.internal_state.keys():
            if "Radial" not in category:
                if item in self.internal_state[category].keys():
                    self.internal_state[category][item] = float(value)
                    if 'Motional' in category:
                        self.CalcLamb_Dicke()
                    if( self.internal_state["Transitions"]['Carrier'] in item 
                        or self.internal_state["Transitions"]['OpticalPumping'] in item):
                        self.CalcBFieldandCenter()
                        self.CalcTransitionFrequencies()
                        timenow = float( datetime.datetime.utcnow().strftime('%s') )
                        self.internal_state["Drift"]["Time1"] = timenow
                    if 'PiTime' in item:
                        self.CalcPiTimes()
            else:
                print 'item does not exist: ',item

        else:
            print 'category does not exist: ',category

    @safely
    def CalcLamb_Dicke(self):
        for freq in self.internal_state["MotionalFrequency"].keys():
            if "eta" not in freq:
                omega_sec = self.internal_state["MotionalFrequency"][freq]
                LD = AtomicHelpers.Lamb_Dicke(2*np.pi*omega_sec*1E6)
                self.internal_state["MotionalFrequency"][freq+"-eta"] = float(LD)

    
    @safely
    def CalcBFieldandCenter(self):
        carrier_state = self.internal_state["Transitions"]["Carrier"]
        op_state      = self.internal_state["Transitions"]["OpticalPumping"]
        carrier_mstates = re.search('5S(.*)-4D(.*)', carrier_state )
        op_mstates = re.search('5S(.*)-4D(.*)', op_state )
        Tcarrier = [{"L":0, 
                     "J":1/2.,
                     "m":mdict[carrier_mstates.group(1)]},
                    {"L":2, 
                     "J":5/2.,
                     "m":mdict[carrier_mstates.group(2)]}]
        dE1 = AtomicHelpers.dE_zeeman(Tcarrier[0], Tcarrier[1])
        Top      = [{"L":0, 
                     "J":1/2.,
                     "m":mdict[op_mstates.group(1)]},
                    {"L":2, 
                     "J":5/2.,
                     "m":mdict[op_mstates.group(2)]}]
        dE2 = AtomicHelpers.dE_zeeman(Top[0], Top[1])

        dE_measured = (self.internal_state["Transitions"][op_state] 
                       - self.internal_state["Transitions"][carrier_state] )
        self.internal_state["BField"]["Bmag"] = float( dE_measured / (dE2 - dE1) )
        self.internal_state["Transitions"]["5S-4D"] = float(self.internal_state["Transitions"][carrier_state] 
                                                       - dE1 * self.internal_state["BField"]["Bmag"] )


    @safely
    def CalcTransitionFrequencies(self):
        for key in self.internal_state["Transitions"]:
            if key not in ['5S-4D','Carrier','OpticalPumping']:
                mstates = re.search('5S(.*)-4D(.*)', key )
                T   =  [{"L":0, 
                         "J":1/2.,
                         "m":mdict[mstates.group(1)]},
                        {"L":2, 
                         "J":5/2.,
                         "m":mdict[mstates.group(2)]}]
                dE = AtomicHelpers.dE_zeeman( T[0], T[1] )
                self.internal_state["Transitions"][key] = float(self.internal_state["Transitions"]["5S-4D"] 
                                                           + dE * self.internal_state["BField"]["Bmag"] )
                self.internal_state["TransitionsRadial"][key] = float(self.internal_state["Transitions"]["5S-4D"] 
                                                           + dE * self.internal_state["BField"]["Bmag"] )/2.
    @safely
    def CalcPiTimes(self):
        carrier_state = self.internal_state["Transitions"]["Carrier"]
        op_state      = self.internal_state["Transitions"]["OpticalPumping"]
        carrier_mstates = re.search('5S(.*)-4D(.*)', carrier_state )
        op_mstates = re.search('5S(.*)-4D(.*)', op_state )
        Tcarrier = [{"L":0, 
                     "J":1/2.,
                     "m":mdict[carrier_mstates.group(1)]},
                    {"L":2, 
                     "J":5/2.,
                     "m":mdict[carrier_mstates.group(2)]}]
        dE1 = AtomicHelpers.dE_zeeman(Tcarrier[0], Tcarrier[1])
        Top      = [{"L":0, 
                     "J":1/2.,
                     "m":mdict[op_mstates.group(1)]},
                    {"L":2, 
                     "J":5/2.,
                     "m":mdict[op_mstates.group(2)]}]

        CBratio = AtomicHelpers.Clebsch_Gordan(*Top) / AtomicHelpers.Clebsch_Gordan(*Tcarrier) 
        self.internal_state["StatePrep"]["PiTime"] = float(self.internal_state["Carrier"]["Z1PiTime"] / CBratio )
        for key in self.internal_state["MotionalFrequency"]:
            if 'eta' not in key:
                self.internal_state["SBCool"]["PiTime-"+key] = ( self.internal_state["Carrier"]["Z1PiTime"] 
                                                    / self.internal_state["MotionalFrequency"][key+"-eta"] )

    @safely
    def LOGGING(self):
        print 'Logging current values...'
        d = datetime.date.today()
        datestring = datetime.datetime.utcnow()
        flstring = ExpLogDir  + "TransitionLogNow.yaml"
        with open(flstring,'a+') as f:
            yaml.dump({datestring:self.internal_state}, f, default_flow_style=False)
        self.UPDATECHEADER()
        self.SAVE()

    @safely
    def UPDATECHEADER(self):
        linevar = '//        GLOBAL        //\n'
        for key in cheaderDict:
            linevar += "\n    //%s\n"%key
            for item in cheaderDict[key]:
                try:
                    print key, item, self.internal_state[key][cheaderDict[key][item]]
                except:
                    pass
                if "Time" in cheaderDict[key][item]:
                    linevar +="    #define %s %i\n"%(item,self.converttime( self.internal_state[key][cheaderDict[key][item]]) )
                elif "Freq" in cheaderDict[key][item]:
                    linevar +="    #define %s %i\n"%(item,self.convertfreq( self.internal_state[key][cheaderDict[key][item]]) )
                elif "F_5S" in item:
                    linevar +="    #define %s %i\n"%(item,self.convertfreq( self.internal_state[key][cheaderDict[key][item]]) )
                elif "F_SB" in item:
                    linevar +="    size_t %s = %i;\n"%(item,self.convertfreq( self.internal_state[key][cheaderDict[key][item]]) )
                elif "SBSequence" in item:
                    Tsb = self.internal_state["SBCool"]["PiTime-zcom"]
                    Nloops = self.internal_state["SBCool"]["Loops"]
                    rng = np.linspace(Nloops,0,Nloops)
                    SBsequence = Tsb / (np.sqrt(1+rng) )
                    linevar +="    int %s[%i] = %s\n"%(item,
                                                          len(SBsequence),
                                                          self.gencarray(SBsequence) )
                else:
                    linevar +="    size_t %s = %s;\n"%(item,self.convert(self.internal_state[key][cheaderDict[key][item]]) )
            if key == "MotionalFrequency":
                for item in cheaderDict[key]:
                    item = item.split('F_')[-1]
                    linevar += "    size_t F_R%s = %s - F_%s;\n"%(item,"F_Carrier",item)
                    linevar += "    size_t F_RS%s = %s - F_%s - F_%s;\n"%(item,"F_Carrier",item,item)
            if key == "StatePrep":
                linevar += "    #define F_1033 %i\n"%( self.convertfreq( self.internal_state[key]["F1033"] ) )
                linevar += "    #define A_1033 %i\n"%( self.internal_state[key]["A1033"])
                linevar += "    #define T_quench %i\n"%( self.converttime(self.internal_state[key]["T1033"] ) )
        linevar += '//      END GLOBAL      //'
        with open(ConstantsFILE,'w+') as f:
            f.write(linevar)

    @safely
    def gencarray(self,arr):
        return '{' + ','.join(str( self.converttime(i) ) for i in arr) + '};'
                
    @safely
    def convertfreq(self, val):
        return int( round(  2**32  * val / simple_dds.CLOCK_FREQ ) )

    @safely
    def converttime(self, val):
        return int( round(  val * simple_dds.CLOCK_FREQ / 32. ) )

    @safely
    def convert(self,val):
        if type(val) == str: return 'F_' + str( val.replace('-4D','_4D').replace('-','n') )
        else: return str( int( val ) )



    @safely         
    def SAVE(self):
        with open(ExperimentValues,'w+') as f:
            yaml.dump(self.internal_state, f, default_flow_style=False)
            
    def STOP(self):
        if self.internal_state:
            self.SAVE()           
        print 'done.'  
             

