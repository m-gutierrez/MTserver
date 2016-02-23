#!/usr/bin/env python
'''
    Written by: Michael Turek 2014-04-01
    Updated: MG 2014-07-20
    
    Description: 
    This script is design to handle many-to-one communication between multiple users
    and a single piece of hardware. 
    In this script a server socket is opened and an instance of the worker created. 
    The server then waits for connections, creates a new thread for each and relays
    messages to the worker.
'''

import socket
import select
import sys
import threading
import Queue
import copy
import time
import errno
import string
import argparse
import struct
import os.path
import json
import traceback
import os

DEBUG = False

try:
    DICT_FILE = os.environ['DEV_DICT']
    print 'Loading device dictionary : %s'%DICT_FILE
except Exception as e:
    print "no global DICT_FILE defined..."
    print 'Is DeviceWorkers installed?...'
    print 'Searching current directory for [devices_dict]...'
    DICT_FILE = "devices_dict"
"""
The Server class is the main entry point of the backend, it listens
for client connections at a particular port and spawns a ClientThread
for each incoming connection.

It also handles the multithreading for the entire backend such that
the Worker thread is implicitly thread safe.
"""
class Server:
    def __init__(self, workerName, port):
        try:
            self.debug = DEBUG
            
            #Get the IP address of host computer
            self.hostname = socket.gethostname()
            self.host = socket.gethostbyname(self.hostname)
            self.port = port
            
            if port == 12345: # default port, look for the device file
                if os.path.isfile(DICT_FILE):
                    self.devices = json.load(open(DICT_FILE))
                    keylist=self.devices.keys()
                    if workerName in keylist:
                        self.port = int(string.split(self.devices[workerName],":")[1])
                        print "Using port %d from device file" %(self.port)

            self.server = None
            self.threads = []
            print 'The worker name is : %s'%(workerName)
            self.worker = Worker(self,string.split(workerName,'Worker')[0])
            self.workerName = workerName

            # self.f = file("messageLog.txt", "w")

            self.deadThreads = []
            self.serverLock = threading.Lock()
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()

    def openSocket(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            self.server.bind((self.host,self.port))
            self.server.listen(5)

            print "Server accepting connections on %s ip:%s port: %s"%(self.hostname,self.host,str(self.port))

        except socket.error, (value,message):
            print "ERROR: Could not open socket: " + message
            self.port=self.port+1
            self.openSocket()
            if self.port > 12500:
                if self.server:
                    self.server.close()
                sys.exit(1)

    def getWorker(self):
        return self.worker

    # TODO: Make sure that nothing can destroy/remove a thread while
    # a long message is being broadcast, is it OK to block the server
    # while sending? -> Probably OK, other thread will allocate memory
    # for the function call and the message won't get lost
    def broadcastMessage(self, message):
        # self.serverLock.acquire()
        #threads = copy.copy(self.threads)
        
        # self.f.write(message)

        for thread in self.threads:
            thread.sendMessage(message)
        
        threadNum = len(self.threads)

        # self.serverLock.release()    

        self.debugMsg("Broadcasting a message to all users: NUM = " + str(threadNum))

    def removeClient(self, clientThread):
        self.serverLock.acquire()

        self.threads.remove(clientThread)
        self.deadThreads.append(clientThread)

        self.serverLock.release()

        print "Client removed from the list"
        print "Length of deadThreads: " + str(len(self.deadThreads))

    def run(self):
        self.openSocket()
        self.worker.start()

        inputSources = [self.server,sys.stdin]
        running = 1

        print "Launching console for " + self.workerName + "...\n"
        print "Enter HELP for a list of commands"

        while running and not self.worker.quitting:
            sys.stdout.write(self.workerName + "> ")
            sys.stdout.flush()

            inputready,outputready,exceptready = select.select(inputSources,[],[])

            for s in inputready:
                if s == self.server:
                    # client,client_address = self.server.accept()

                    client = self.server.accept()

                    clientThread = ClientThread(client, self)
                    print "Client connected:" + str(clientThread.address)
                    clientThread.start()

                    self.serverLock.acquire()
                    self.threads.append(clientThread)
                    self.serverLock.release()


                    # Process zombie clients:
                    self.serverLock.acquire()

                    while len(self.deadThreads) > 0:
                        thread = self.deadThreads[0]
                        thread.join()
                        self.deadThreads.remove(thread)

                        print "Zombie removed"

                    self.serverLock.release()

                elif s == sys.stdin:
                    text = sys.stdin.readline().rstrip()
                    try:
                        if text == 'HELP':
                            print "The available commands are: \n\tHELP \n\tSTATUS \n\tDEVICESTATUS \n\tKILL"
                        elif text == 'STATUS':
                            print "Server running on ip: %s port: %s"%(self.host,str(self.port))
                            print "Current number of connected clients: " + str(len(self.threads))
                            for i in self.threads:
                                print '\tClient: %s @%s:%i\n'%(socket.gethostbyaddr(i.address[0])[0],i.address[0],i.address[1])
                        elif text == 'DEVICESTATUS':
                            print "Current Device state: "
                            self.worker.acceptTask('PUPDATE')
                        elif 'CMD' in text:
                            cmd = text.split('CMD ')[1]
                            print 'Processing command %s \n'%cmd
                            self.worker.acceptTask(cmd)
                        elif text == "":
                            print ''
                        elif text == 'KILL':
                            running = 0
                        else:
                            print "Command not recognized, enter HELP to see the list of available commands."
                    except Exception as e:
                        print 'terminal cmd error: \n',e
                        pass

                    

        # Shut down all sockets
        print "Shutting down..."
        self.server.close()
        print "Server socket closed"
        KillList = self.threads
        for thread in KillList:
            thread.kill()
            thread.join()
        DeadList = self.deadThreads
        for thread in DeadList:
            thread.join()

        self.worker.kill()
        self.worker.join()

        # self.f.close()

        print "Everything is dead"

    # If the debug flag is set to True, print msg to stdout
    def debugMsg(self, msg):
        if self.debug:
            print msg


"""
The ClientThread implements a connection with a single client

It listens at the assigned socket for incoming messages
from the client and distributes server broadcasts to them.

By default, the maximum length of a message can be 1024B.
"""
class ClientThread(threading.Thread):
    def __init__(self,(client,address), server):
        threading.Thread.__init__(self)

        self.debug = DEBUG

        self.server = server
        self.client = client
        self.address = address
        self.running = 1

    # Listen to messages from the client and forward them
    # to the worker thread when they arrive
    def run(self):
        # Force an initial update        
        self.server.getWorker().acceptTask("UPDATE")

        while self.running:
            data = self.client.recv(8192)
            if data:
                self.debugMsg("A client sent data: (" + data + ")")

                # Remove new line at the end of the message
                data = data.rstrip("\n\r")
                dataArray = data.split('\n')
                # TODO: add a filter for server-side tasks
                # TODO: handle the DISCONNECT message
                for i in dataArray:
                    self.server.getWorker().acceptTask(i)

            else:
                self.debugMsg("recv returned null: connection interrupted")
                self.kill()
    
    # Send a given message to the client socket   
    # Prefixed with message length for unpacking
    # See http://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data 
    def sendMessage(self, msg):
        try:
            msg = struct.pack('>I', len(msg)) + msg
            self.client.sendall(msg)

        except socket.error, e:
            print "ERROR: Socket invalidated while sending"
            self.kill()

    def kill(self):
        if self.running == 1:
            self.running = 0

            try:
                self.debugMsg("Killing the client connection")
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
            
            except socket.error, e:
                if isinstance(e.args, tuple):
                    if e[0] == errno.ENOTCONN:
                        self.debugMsg("Closing the socket failed (Socket already closed)")
                    else:
                        self.debugMsg(str(e.args))
                else:
                    self.debugMsg("Error while closing the client connection: " + str(e))

            finally:
                self.server.removeClient(self)

    # If the debug flag is set to True, print msg to stdout
    def debugMsg(self, msg):
        if self.debug:
            print msg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal server black-boxing the communication with individual equipment")

    parser.add_argument("worker", help="specify the Worker module you want to communicate with")
    parser.add_argument("-p", "--port", default=12345, type=int, help="specify the port at which you want to broadcast")
    parser.add_argument("-d", "--debug", action="store_true", help="enable debug messages")

    args = vars(parser.parse_args(sys.argv[1:]))

    import importlib
    Worker = importlib.import_module("MTWorker").Worker
    DEBUG = args["debug"]

    try:
        import procname
        procname.setprocname(args["worker"])
    except:
        print "Procname module not found. Using default procname: python"

    server = Server(args["worker"], args["port"])
    server.run()
