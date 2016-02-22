'''
    Written by: Michael Turek
    2014-04-01
    Updated: MG 2014-07-20
    
    Description: 
    This script is designed to interface between a device
    communication class and a server script. It's goal is to make device 
    side communication single threaded while allowing multiple users to 
    simultaneously pass commands to it in a conflict free manner. This is 
    handled in two stages, server side and worker side. Here, the worker side
    maintains single threading by processing tasks from a python queue, pythons
    queue library is thread safe.
    
'''
import socket
import select
import sys
import threading
import Queue
import copy
import time
import errno
import os
import traceback
DEBUG = False



"""
The Worker class handles the control of the physical device 
and is the only component that needs to be adapted on a 
device to device basis.


The methods to be implemented are:
1) processTask(self,task) which determines how the 
    device should react to a particular request

2) sendStatusUpdate(self) which determines how the 
    readout of the equipment should be encoded into 
    a message for the clients

Any additional methods can be defined as well as any 
necessary data fields. The access will be thread-safe
as long as all the methods are only called from the 
default ones and not directly by the server.
"""



class Worker(threading.Thread):
    def __init__(self, server,workerName):

        threading.Thread.__init__(self)
        
        self.server = server
        self.workQueue = Queue.Queue(maxsize=0)
        self.running = 1
        self.quitting = 0

        ### Device specific setup and data ###
        import importlib 
        self.devicecomm = importlib.import_module('DeviceWorkers.%sComm'%(workerName)).Comm()
        self.availablecommands = dir(self.devicecomm)
        
        self.DEFAULT_UPDATE_INTERVAL = 1 # in sec

        ######################################

        self.updater = Updater(self, self.DEFAULT_UPDATE_INTERVAL)
        self.updater.start()
        
    # Main worker loop, blocks until there is a task
    # waiting in workQueue, then it processes it
    def run(self):
        while self.running == 1:
            task = self.workQueue.get()
            self.processTask(task)
            self.workQueue.task_done()

    # Describes how a particular device should react
    # to incoming messages.
    #
    # Each message is assumed to be of the form:
    # <TYPE> <ARG1> <ARG2> ...
    def processTask(self,task):
        task = task.rstrip()
        if len(task) <= 3:
            return
        taskArray = task.split(" ")
        taskType = taskArray[0]
        taskArgs = taskArray[1:]

        try:
            if taskType in self.availablecommands or taskType == "":
                #Check if task is available in comm class
                #If available, get handle for method and call with passed args
                getattr(self.devicecomm,taskType)(*taskArgs)
                self.sendStatusUpdate()
            elif taskType == "METHODSAVAILABLE":
                self.sendStatusUpdate(getattr(self.devicecomm,taskType)(*taskArgs), "METHODS")
            elif taskType == "UPDATEINTERVAL":
                try:          
                    self.updater.changeTimeInterval(float(taskArgs[0]))
                except Exception as e:
                    print 'Error when changing update interval: ', e
                    print traceback.format_exc()
            elif taskType == 'PUPDATE':
                print "STATUS " + str(time.time()) + " "+str(self.devicecomm.internal_state)
            elif taskType.startswith("PLOT"): #plots have unique IDs embedded in header
                self.devicecomm.UPDATE()
                self.sendStatusUpdate(self.devicecomm.internal_state, taskType)
            elif taskType.startswith("SPECIALREQUEST"): 
                #Requests specific data from the worker
                #Format SPECIALREQUEST UPDATE;READ;OVEN 1.1;CURRLIM 5.1
                #etc..
                try:
                    specstring = "".join(taskArgs)
                    specialtasks = specstring.split(';')
                    reqData = {}
                    for req in specialtasks:
                        reqArray = req.split(" ")
                        reqType = reqArray[0]
                        reqArgs = reqArray[1:]
                        reqData[reqType] = getattr(self.devicecomm,reqType)(*reqArgs)
                    
                    self.sendStatusUpdate(reqData, taskType)
                except Exception as e:
                    print 'Error in processing special task',e
                    print traceback.format_exc()
            else:
                print "Task not recognized: (" + task + ")"
                print "taskType: ("+taskType+")"
                print "Available commands (%s)"%(str(self.availablecommands))
        except Exception as e:
            print 'Failed in processTask: ',e
            print traceback.format_exc()

    # Encodes the UPDATE message to be distributed to the clients
    # This can be a readout from the device or any other kind of 
    # notification
    #
    # Each message should be of the form:
    # STATUS <ARG1> <ARG2> ...
    def sendStatusUpdate(self,DATA = None,HEADER = None):
        ### Define the arguments to send ########
        
        #########################################

        if DATA == None and HEADER == None:
            message = "STATUS " + str(time.time()) + " "+str(self.devicecomm.internal_state)
        else:
            message = str(HEADER)+" " + str(time.time()) + " "+ str(DATA)
        self.server.broadcastMessage(message)


    # Adds a task to the worker's workQueue. Can be called by the 
    # server or directly from the Worker thread
    def acceptTask(self, task):
        self.workQueue.put(task)


    def kill(self):
        self.running = 0
        self.workQueue.put("STOP") 
        
        self.updater.kill() 
        self.updater.join() 


"""
The Updater class implements a simple timer which
forces the Worker to send a status update to all
clients at predetermined points in time
"""
class Updater(threading.Thread):
    def __init__(self, worker, timeInterval):
        threading.Thread.__init__(self)
        self.worker = worker
        self.timeInterval = timeInterval

        self.changeTimeQueue = Queue.Queue(maxsize=0)
        

        self.running = 1

    # If there is no waiting time interval change request,
    # send an UPDATE message to the worker and waits for
    # a period of time set in self.timeInterval (in seconds)
    def run(self):
        while self.running == 1:
            if self.timeInterval > 1: # if interval is large, we still want to respond to external updates
                for i in range(int(self.timeInterval)):
                    if not self.changeTimeQueue.empty():
                        self.timeInterval = self.changeTimeQueue.get()
                        self.changeTimeQueue.task_done()
                        if self.timeInterval < i+1:
                            break
                    time.sleep(1)
            else:
                time.sleep(self.timeInterval)
                if not self.changeTimeQueue.empty():
                    self.timeInterval = self.changeTimeQueue.get()
                    self.changeTimeQueue.task_done()
            self.worker.acceptTask("UPDATE")

    # Places a request to change the time interval in the
    # changeTimeQueue. This request will be processed at the
    # beginning of the next update cycle
    def changeTimeInterval(self, newTimeInterval):
        self.changeTimeQueue.put(newTimeInterval)

    def kill(self):
        self.running = 0
    
