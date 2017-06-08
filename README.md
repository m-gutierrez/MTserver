# MTServer


	- MTServer, for black-boxing device communication.
	- Written by: Michael Turek, Michael Gutierrez, Helena Zhang 2014


A simple socket-server for black-boxing device communication, providing a common framework for many-to-one communication for disparate devices. 


# server 
This script is design to handle many-to-one communication between multiple users
and a single piece of hardware. 
In this script a server socket is opened and an instance of the worker created. 
The server then waits for connections, creates a new thread for each and relays
messages to the worker.


The Server class is the main entry point of the backend, it listens
for client connections at a particular port and spawns a ClientThread
for each incoming connection.
It also handles the multithreading for the entire backend such that
the Worker thread is implicitly thread safe.


# worker 

This script is designed to interface between a device
communication class and a server script. It's goal is to make device 
side communication single threaded while allowing multiple users to 
simultaneously pass commands to it in a conflict free manner. This is 
handled in two stages, server side and worker side. Here, the worker side
maintains single threading by processing tasks from a python queue, pythons
queue library is thread safe.

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