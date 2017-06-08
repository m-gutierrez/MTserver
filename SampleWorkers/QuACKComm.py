"""
    QuackComm.py: MTworker for interfacing with QuACK. Grabbing and setting idle-state variables through simple_dds 
    and loading full quack scripts through RUNSCRIPT. Special message commands for script data through quack data-pipe READOUT. 
    Further runs simulation files for generating on-the-fly voltage settings given desired trap specifications e.g. Secular frequency, 
    motional-axis, trapping locations.
    MG,RRINES: 2016-01-05
"""
from __future__ import division
import quackCon.qc_comm as qc_comm
import quackCon.simple_dds as simple_dds
import time
import importlib
import numpy as np
import collections
import pathos.multiprocessing as mp #allows mp.Pool to be used with classmethods

CLOCK_FREQ          = 2048
RunFolder           = '/home/twins/Dropbox (MIT)/Quanta/Twins/Control Software/quackCon/'
DEBUG               = False
simple_dds.CLOCK_FREQ = CLOCK_FREQ
if DEBUG:
    simple_dds.DEBUG=DEBUG


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

class Comm():
    def __init__(self):
        try:
            #Initialize QuACK
            print 'Initializing simple_dds.py...'
            dev='lx150'
            self.simple = simple_dds.simple_dds(quack_dir = RunFolder)
            time.sleep(1)
            self.simple.setup_clock(1,1)
            if DEBUG: 
                simple_dds.DEBUG= DEBUG

            print 'QuACK quack'
        except Exception as e:
            print 'ERROR could not initialize QuACK: \n',e
            raise


        try:
            self.QuACK_Config = {}
            #Clock
            self.QuACK_Config["MasterClock"]= CLOCK_FREQ 
            #DDS hardware
            self.QuACK_Config["#DDS_cards"] = 4
            self.QuACK_Config["DDS1"]       = 1
            self.QuACK_Config["DDS2"]       = 2
            self.QuACK_Config["DDS3"]       = 3
            self.QuACK_Config["DDS4"]       = 4
            #DAC hardware
            self.QuACK_Config['DAC RAIL']   = 10.0
            self.QuACK_Config["#DAC_cards"] = 4
            self.QuACK_Config["DAC6"]       = 6
            self.QuACK_Config["DAC7"]       = 7
            self.QuACK_Config["DAC8"]       = 8
            self.QuACK_Config["DAC9"]       = 9

            #LED
            self.QuACK_Config["LEDB1"]      = 11
            self.QuACK_Config["LEDB2"]      = 14
            self.QuACK_Config["LEDB3"]      = 12
            self.QuACK_Config["LEDR1"]      = 13
            self.QuACK_Config["LEDR2"]      = 15
            self.QuACK_Config["LEDR3"]      = 16
            self.QuACK_Config["LEDY1"]      = 17
            self.QuACK_Config["LEDY2"]      = 18
            self.QuACK_Config["LEDY3"]      = 19
            self.voltage_set = { 'DAC%i-%i'%( 6+int(i/12),i%12 ) : 0 for i in range(0,48) }



            import importlib 
            from Maps.ElectrodeMap import electrode_hoa_dict
            self.ElectrodeDACMap = electrode_hoa_dict

            self.internal_state = {}
            #Initialize DDS variables
            for i in range(0,12):
                #Freq:0 - 2**32
                #Amp: 0 - 2**12
                #phase: 0 - 2**14
                #phase mode: Coherent / continuous
                try:
                    ddslabel = self.QuACK_Config["DDS%i"%i] 
                    self.internal_state["DDS%i-0_FREQ"%ddslabel] = 0
                    self.internal_state["DDS%i-1_FREQ"%ddslabel] = 0
                    self.internal_state["DDS%i-0_AMP"%ddslabel]  = 0
                    self.internal_state["DDS%i-1_AMP"%ddslabel]  = 0
                    self.internal_state["DDS%i-0_Phase"%ddslabel]= 0
                    self.internal_state["DDS%i-1_Phase"%ddslabel]= 0
                    self.internal_state["DDS%i-0_Pmode"%ddslabel]= 0
                    self.internal_state["DDS%i-1_Pmode"%ddslabel]= 0
                except:
                    pass

            #Initialize DAC variables
            for i in range(0,12):
                #Volt: 0 - 2**20
                try:
                    daclabel = self.QuACK_Config['DAC%i'%(i)]
                    for j in range(0,12):
                        #time.sleep(0.01)
                        self.QuACK_Config["DAC%i-%i"%(daclabel,j)] = 0#self.simple.getDAC(i,j)
                except:
                    pass

            #Initialize trap potential variables
            for i in range(0,2):
                self.internal_state["TRAP-USE%i"%i]       = False
                self.internal_state["TRAP-Position%i"%i]  = 650   #micron
                self.internal_state["TRAP-Ex%i"%i]        = 0     #V/mm
                self.internal_state["TRAP-Ey%i"%i]        = 0     #V/mm
                self.internal_state["TRAP-Ez%i"%i]        = 0     #V/mm
                self.internal_state["TRAP-OmegaZ%i"%i]    = 0.5   #2piMHz
                self.internal_state["TRAP-XY%i"%i]        = 0     #2piMHz
                self.internal_state["TRAP-XZ%i"%i]        = 0     #2piMHz
                self.internal_state["TRAP-YZ%i"%i]        = 0     #2piMHz
                self.internal_state["TRAP-X2Y2%i"%i]      = 0     #2piMHz

            self.internal_state["TRAP-LOAD"]          = 450


            #Zone 1
            self.internal_state["TRAP-USE%i"%0]       = 1
            self.internal_state["TRAP-Position%i"%0]  = 1760  
            self.internal_state["TRAP-Ex%i"%0]        = -0.06     
            self.internal_state["TRAP-Ey%i"%0]        = 0.00     
            self.internal_state["TRAP-Ez%i"%0]        = 0     
            self.internal_state["TRAP-OmegaZ%i"%0]    = 1.25  
            self.internal_state["TRAP-XY%i"%0]        = 1.5
            #Zone 2     
            self.internal_state["TRAP-USE%i"%1]       = 1
            self.internal_state["TRAP-Position%i"%1]  = 2455  
            self.internal_state["TRAP-Ex%i"%1]        = 0     
            self.internal_state["TRAP-Ey%i"%1]        = 0.00     
            self.internal_state["TRAP-Ez%i"%1]        = 0     
            self.internal_state["TRAP-OmegaZ%i"%1]    = 1.25 
            self.internal_state["TRAP-XY%i"%1]        = 1.5     


            self.internal_state["TRAP-USE2"]       = False

            for i in range(0,10):
                self.internal_state["DB%i"%i] = 0
            #Import trap simulation class
            import Simulation.TrapSimulation.TrapSimulation as TrapSimulation
            dirname="/home/twins/Dropbox (MIT)/Quanta/Twins/Data/HOA2-manual/Attachments/VoltageArray/"
            flname = "RS1096_12400_1" 
            self.trapsim = TrapSimulation.TrapSim(dirname,flname)
            for key in electrode_hoa_dict.keys():
                print '%*s \t : %s'%(7,key,electrode_hoa_dict[key])


            #intialize pmt variable
            self.internal_state["scriptrv"] = 0
            self.internal_state["CORR"] = 0
            self.internal_state["State"] = self.simple.qc.get_state()
            #initialize clock status variable
            self.internal_state["clock_status"] = "0"
            self.clock_status()
            self.simple.send('pmt')


            self.scriptcount  = 0
            #Get current values 
            print 'Clock status : %s'%self.internal_state["clock_status"]
        except Exception as e:
            print 'ERROR in initialization: \n',e

    @safely
    def scriptcounts(self):
        print self.scriptcount
    @safely
    def UPDATE(self):
        self.internal_state["State"] = self.simple.qc.get_state()
        self.ParseMessage()       

        self.GETPMT()

    @safely
    def GETPMT(self):
        if self.internal_state["State"] == 'simple':

            Z2pmtdata = np.array( np.array(self.simple.qc.update_corr(0)[:182])/(250/182.) )
            Z1pmtdata = np.array( np.array(self.simple.qc.update_corr(1)[:52])/(250/52.) )


            self.internal_state["PMTZ1"] = np.mean(Z1pmtdata)
            self.internal_state["PMTZ2"] = np.mean(Z2pmtdata)
            
            self.internal_state["CORR"]= [[ i / 10.0, (Z1pmtdata - self.internal_state["PMTZ1"])[i] ] for i in range(len(Z1pmtdata))]

            self.internal_state["MMampZ1"] = np.max( np.abs( np.fft.hfft(Z1pmtdata -self.internal_state["PMTZ1"] ) ) ) / ( len(Z1pmtdata) / 4.)
            self.internal_state["MMampZ2"] = np.max( np.abs( np.fft.hfft(Z2pmtdata -self.internal_state["PMTZ2"] ) ) ) / ( len(Z2pmtdata) / 4.)

            histZ1 = np.histogram(Z1pmtdata, bins='auto')
            histZ2 = np.histogram(Z2pmtdata, bins='auto')

            self.internal_state["PMT_HISTZ1"] = [ [histZ1[1][i+1], histZ1[0][i] ] for i in range(0,len(histZ1[0]) ) ]
            self.internal_state["PMT_HISTZ2"] = [ [histZ2[1][i+1], histZ2[0][i] ] for i in range(0,len(histZ2[0]) ) ]

            self.simple.send('pmt')

    @safely
    def ParseMessage(self):
        rv_msg = (self.simple.qc.sysout.get()).split('\n')
        for msg in rv_msg:
            if 'ret: 0x0' in msg:
                self.internal_state["Busy"] = 0
                self.internal_state["scriptrv"] = "returned"
                self.simple.send('pmt')
                print 'Script returned...'
            elif 'freq:' in msg:
                spltmsg = msg.split(':')
                freqs = np.array(spltmsg[1].split(' ')).astype(int) * CLOCK_FREQ / 2.**32
                rv = ' '.join(['%.6f'%f for f in freqs])
                parsedmsg = '%s: %s'%(spltmsg[0],rv)
                print parsedmsg
                self.internal_state["scriptrv"] = parsedmsg
            elif 'time:' in msg:
                spltmsg = msg.split(':')
                times = np.array(spltmsg[1].split(' ')).astype(int) * 32.0 / CLOCK_FREQ
                rv = ' '.join(['%.3f'%t for t in times])
                parsedmsg = '%s: %s'%(spltmsg[0],rv)
                print parsedmsg
                self.internal_state["scriptrv"] = parsedmsg
            elif 'volt:' in msg:
                spltmsg = msg.split(':')
                dac = int(spltmsg[1])
                if dac >= 2**19: 
                    dac += -2**32
                rv = dac * simple_dds.DAC_RAIL / 2**19
                parsedmsg = '%s: %.6fV'%(spltmsg[0],rv)
                self.internal_state["scriptrv"] = parsedmsg
                print parsedmsg
            elif 'Start loading...' in msg:
                self.internal_state["scriptrv"] = "accepting input"
                print 'Accepting input ...'
            elif msg != '':
                print 'msg: ',msg

    @safely
    def clock_status(self):
        clockstatus = "{0:b}".format(self.simple.clock_status())
        if clockstatus != self.internal_state["clock_status"]:
            self.internal_state["clock_status"] = clockstatus
        print clockstatus
        

    @safely
    def Reset_DDS(self,chan):
        chan = int(chan)
        self.simple.resetDDS(chan)

    @safely
    def Reset_clock(self, chan = 1, dds = 1):
        self.simple.setup_clock(chan,dds)

    @safely
    def Reset_Simple(self):
        self.simple.reset_simple_dds()
        time.sleep(1)
        self.Reset_clock()
        time.sleep(1)
        self.simple.send('pmt')

    @safely
    def Reset(self):
        """
            Description
            -----------
            resets all devices 
        """
        if not self.simple.check_alive():
            print 'Simple_dds not running, restarting...'
            self.simple.stopScript()
            time.sleep(.3)
            #self.send(*["NOP"]*8) 
            # Add devices from devlist:
            self.simple.reset_all()    
        else:
            self.simple.reset_all()
        self.Reset_clock()

    @safely
    def Reset_fpga(self):
        self.simple.reset_fpga()
        time.sleep(5)
        self.Reset()
        self.simple.send('pmt')

    @safely
    def SHUTTLE(self, param):
        if param == "LOAD":
            xstart = int( (self.internal_state["TRAP-LOAD"] - 300)/10. )
            self.simple.send('sht',xstart)
        elif param == "Z1toZ2":
            self.simple.send('zon',0)
        elif param == "Z2toZ1":
            self.simple.send('zon',1)
        else:
            print 'Oops not a valid shuttle command...'


    @safely
    def SPLIT(self,param):
        if param == "fwd":
            self.simple.send('spl',0)
        elif param == "bwd":
            self.simple.send('spl',1)
        else:
            print 'Oops not a valid shuttle command...'

    @safely
    def TRAP(self,param, val=0):
        val = float(val)
        param = str(param)
        RAIL = self.QuACK_Config['DAC RAIL'] 
        print "Setting TRAP-%s = %f"%(param,float(val))
        self.internal_state["TRAP-%s"%param] = float(val)
        if param != 'LOAD':
            mp_constraint = collections.OrderedDict()
            x_trap = collections.OrderedDict()
            for i in range(0,3):
                if self.internal_state['TRAP-USE%i'%i]:
                    #[Ex,Ey,Ez,xy,yz,z^2-x^2-y^2, z x, x^2 - y^2]

                    mp_constraint[i] = np.array([[0, self.internal_state["TRAP-Ex%i"%i]],
                                             [1, self.internal_state["TRAP-Ey%i"%i]],
                                             [2, self.internal_state["TRAP-Ez%i"%i]],
                                             [3, self.internal_state["TRAP-XY%i"%i]**2],
                                             [4, self.internal_state["TRAP-YZ%i"%i]**2],
                                             [5, self.internal_state["TRAP-OmegaZ%i"%i]**2],
                                             [6, self.internal_state["TRAP-XZ%i"%i]**2],
                                             [7, -self.internal_state["TRAP-X2Y2%i"%i]**2]
                                             ])
                    x_trap[i] = 2308.5*2 - self.internal_state['TRAP-Position%i'%i]



            mp = np.array([ mps for i,mps in mp_constraint.items()])
            x_traps = np.array([x for i,x in x_trap.items() ] )
            self.voltage_set = self.trapsim.GenerateVoltages2(x_traps, 
                            [], 
                            mp)
                            #[ self.voltage_set[key] for key in self.trapsim.dackeys])
            #for key in self.voltage_set.keys():
            #    print '%*s \t : %s'%(7,key, self.voltage_set[key]) 
            voltages = [ int((2**19/RAIL )*self.voltage_set[key]) for key in self.trapsim.dackeys]
            self.simple.send('arr',*voltages)

    @safely
    def GETDACVOLTAGES(self):
        for i in range(0,12):
            #Volt: 0 - 2**20
            try:
                daclabel = self.QuACK_Config['DAC%i'%(i)]
                for j in range(0,12):
                    time.sleep(0.1)
                    print 'DAC%i-%i : '%(i,j), self.simple.getDAC(i,j) 
            except Exception as e:
                #print e
                pass

    def LOADELECTRODES(self,voltage_file):
        try:
            voltage_file = 'Voltage_solutions.'+str(voltage_file)
            voltage_dict = importlib.import_module(voltage_file).electrode_values

            #set all to zero
            for i in range(0, 12):
                try:
                    daclabel = self.QuACK_Config['DAC%i'%(i)]
                    for j in range(0,12):
                        self.DAC(i,j,0.0)
                except:
                    pass    
            for key in voltage_dict.keys():
                self.ELECTRODE(key,voltage_dict[key])
            self.DACUPDATE()
        except Exception as e:
            print 'ERROR in LOADELECTRODES: \n',e
    @safely
    def dacIdentity(self,scale=1):
        scale = float(scale)
        for i in range(0, 12):
            try:
                daclabel = self.QuACK_Config['DAC%i'%(i)]
                for j in range(0,12):
                    self.DAC(i,j,scale*(1.2*(i-6)+j*0.1))
                self.DACUPDATE()
            except Exception as e:
                pass
    @safely
    def DACID(self,scale=1.0):
        scale = float(scale)
        RAIL = 10.0
        vset = np.arange(0,48*0.1*scale,0.1*scale)
        v = [ int((2**19/RAIL )*x ) for x in vset]

        self.simple.send('arr',*v)

    def ELECTRODE(self, seg, v):
        try:
            if DEBUG: print seg,v
            seg        = str(seg)
            v          = float(v)
            [chan,dac] = (self.ElectrodeDACMap[seg]).strip('DAC').split('-')
            self.DAC(chan,dac,v)
            print '%*s \t: %f'%(7,seg,v)
        except Exception as e:
            print 'ERROR in ELECTRODE: \n',e

    def GETELECTRODE(self, seg):
        try:
            seg        = str(seg)
            [chan,dac] = (self.ElectrodeDACMap[seg]).strip('DAC').split('-')
            print 'DAC%i-%i : '%(int(chan),int(dac)), self.simple.getDAC(chan,dac) 
        except Exception as e:
            print 'ERROR in ELECTRODE: \n',e

    def GETELECTRODES(self):
        try:
            for seg in self.ElectrodeDACMap.keys():
                [chan,dac] = (self.ElectrodeDACMap[seg]).strip('DAC').split('-')
                print '%s - DAC%i-%i : '%(seg,int(chan),int(dac)), self.simple.getDAC(chan,dac) 
        except Exception as e:
            print 'ERROR in ELECTRODE: \n',e
    @safely
    def DAC(self,chan,dac,v):

            v    = float(v)
            chan = int(chan)
            dac  = int(dac)
            if abs(v) < 10:
                self.simple.setDAC(chan,dac,v)
                self.QuACK_Config["DAC%i-%i"%(chan,dac)] = v
            else:
                print '!!!!Voltage out of DAC range!!!!'


    # Update all the DACs (or optionally just the ones listed):
    @safely
    def DACUPDATE(self,*args):
        self.simple.updateDACs()

    @safely
    def FREQ(self,chan,dds,f = 0):
        if DEBUG: print chan,dds,f
        chan    = int(chan)
        dds     = int(dds)
        f       = float(f)
        param   = "DDS%i-%i"%(chan,dds)

        self.simple.setFreq(chan,dds,f)

        self.internal_state[param+"_FREQ"] = f

    @safely
    def AMP(self,chan,dds,a = 0):

        if DEBUG: print chan,dds,a
        chan    = int(chan)
        dds     = int(dds)
        a       = int(float(a))
        param   = "DDS%i-%i"%(chan,dds)
        self.simple.setAmp(chan,dds,a)
        self.internal_state[param+"_AMP"] = a
        
    @safely
    def PHASE(self,chan,dds,val):
        chan    = int(chan)
        dds     = int(dds)
        val     = int(val)
        param   = "DDS%i-%i"%(chan,dds)
        print chan, dds, val
        self.simple.setPhase(chan,dds,val)
        self.internal_state[param+"_PHASE"] = val

    @safely
    def DB(self,pin,val):
        pin = int(pin)
        val = int(val)
        #print 'Calling set DB with pin=%i and val = %i'%(pin,val)
        self.simple.setDB(pin,val)
        self.internal_state["DB%i"%pin] = val

    @safely
    def RUNSCRIPT(self,scriptname, script_plot_xscale = 1, script_plot_yscale = 1, script_plot_start = 0, script_plot_stop = -1,typ='pmt'):
        self.scriptcount +=1
        #self.DB(self.QuACK_Config["LEDY1"], 0 )
        self.internal_state["Busy"] = 1
        self.script_plot_start  = int(script_plot_start)
        self.script_plot_stop   = int(script_plot_stop)
        self.script_plot_xscale = float(script_plot_xscale)
        self.script_plot_yscale = float(script_plot_yscale)
        self.script_readout_type = typ
        self.simple.runScript(scriptname)
        time.sleep(0.1)

    @safely
    def SCRIPTSEND(self,*val):
        print val
        data_type = str(val[0])
        id_str = str(val[1])
        if data_type == 'freq':
            val_arr = [int( round( 2**32 * float(i) / simple_dds.CLOCK_FREQ ) )  for i in val[2:]]
        elif data_type == "time":
            val_arr = [int( round( (simple_dds.CLOCK_FREQ) * float(i) / 32. ) )  for i in val[2:]]
        elif data_type == "volt":
            val_arr = [int( round( float(i) * 2**19 / (simple_dds.DAC_RAIL)   ) )  for i in val[2:]]
        elif data_type == 'stp':
            self.simple.send('stp')
            return
        else:
            val_arr = [int(i) for i in val[2:]]

        self.simple.send(id_str,*val_arr)
    @safely
    def send(self, param, val):
        self.simple.send(param, val)
    @safely
    def READOUTcorr(self): 
        corr_arr = np.array(self.simple.qc.update_corr(0)[2000:4000])
        print max(corr_arr)

        return [ [ self.script_plot_xscale * i, self.script_plot_yscale * corr_arr[i] ] for i in range(0,len(corr_arr)) ]
    @safely
    def READOUT(self):
        if self.script_readout_type == "pmt":
            plot_arr = np.array(self.simple.qc.update_plot()[self.script_plot_start:self.script_plot_stop])
            return [ [ self.script_plot_xscale * i, self.script_plot_yscale * plot_arr[i] ] for i in range(0,len(plot_arr)) ]
        elif self.script_readout_type == "corr":
            corr_arr = np.array(self.simple.qc.update_corr(0)[2000:6000])
            print max(corr_arr)
            return [ [ self.script_plot_xscale * i, self.script_plot_yscale * corr_arr[i] ] for i in range(0,len(corr_arr)) ]

    @safely
    def SIMPLE(self):
        self.internal_state["Busy"] = 0
        self.simple.stopScript()
        time.sleep(0.5)
        #self.simple.init_simple_dds()
        #self.DB(self.QuACK_Config["LEDY1"], 1 )
        self.simple.send('pmt')

        #self.internal_state["clock_status"] = clockstatus
        # self.DB(self.QuACK_Config["LEDY3"], int(clockstatus[-1]) )
        # self.DB(self.QuACK_Config["LEDY2"], int(clockstatus[-3]) )
        # self.DB(self.QuACK_Config["LEDR1"], int(clockstatus[-4:] != '1111'))

    def STOP(self):
        try:
               self.simple.stopScript()
        except Exception as e:
            print 'ERROR Failed to stop: \n',e

