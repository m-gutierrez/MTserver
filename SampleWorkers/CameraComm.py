"""
    MTworker for interfacing Andor Luca R camera. Grab image and set camera settings
    Uses Micro-Manager wrapper for the Andor SDK
    MG: 2016-01-05
"""
from __future__ import division
import time
import numpy as np
import collections
import MMCorePy
from PIL import Image
from matplotlib.pyplot import cm
import cv2
IMG_PATH = "FILE" 
BG_PATH = "FILE" 

DEBUG    = False


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
            #Initialize camera
            self.mmc = MMCorePy.CMMCore()
            self.mmc.loadDevice('cam', 'Andor', 'Andor')
            self.mmc.initializeDevice('cam')
            self.mmc.setCameraDevice('cam')

            #define storage variables
            self.internal_state = {}
            self.internal_state["counts"]   = 0
            self.internal_state["maxCounts"]= 0
            self.internal_state["Gain"]     = 400
            self.internal_state["Exposure"] = 200

            #Set default state
            ROI = [ 530,    #x0
                    0,      #y0
                    1004,   #dx
                    150]    #dy
            self.mmc.setProperty('cam', 'PixelType', '16bit')
            self.mmc.setROI(*ROI)
            self.mmc.setProperty('cam', 'Gain', self.internal_state["Gain"])
            self.mmc.setProperty('cam', 'Exposure', self.internal_state["Exposure"])


            self.bg = np.zeros((ROI[2],ROI[3]))
            self.grid = np.zeros((ROI[2],ROI[3],4))

            # specific grid, sometimes useful
            # for i in range(10):
            #     cv2.line(self.grid,(100*i-4,0),(100*i-4,150),(125,125,125),1)
            # cv2.line(self.grid,(0,25),(1004,25),(125,125,125),1)
            # cv2.line(self.grid,(0,100),(1004,100),(125,125,125),1)
            cv2.circle(self.grid,(106,135),20,(125,125,125),1)
            #cv2.circle(self.grid,(879,77),20,(125,125,125),1)

            #Take initial image
            #self.mmc.snapImage()
            #matimg.imsave(IMG_PATH, self.mmc.getImage())

        except Exception as e:
            print 'ERROR in initialization: \n',e

    @safely
    def UPDATE(self):
        self.getImage()

    @safely
    def GETBG(self,reset = 0):
        if not reset:
            self.mmc.snapImage()
            self.bg = self.mmc.getImage().astype(np.int32)
        else:
            self.bg = np.zeros((150,1004))


    @safely
    def getImage(self):
        self.mmc.snapImage()
        img = self.mmc.getImage().astype(np.int32)
        self.internal_state["maxCounts"] = np.max(img[50:100,:])
        img = np.abs((img - self.bg))
        #self.internal_state["countarr"] = [[i,int(np.sum(img[25:50,25*i:25*(i+1)] )/5E3)] for i in range(40)]
        self.internal_state["counts1"] = np.max(np.sum(img[35:55,264:284]))
        self.internal_state["counts2"] = np.max(np.sum(img[67:87,869:889]))
        img = (img * 255/ np.max(img)).astype('uint8')
        cv2.imwrite(IMG_PATH,cm.inferno(img)*255+self.grid)
        #im.save(IMG_PATH)


    @safely 
    def SETPROPERTY(self, Property,val):
        Property = str(Property)
        val = int(val)
        print 'Setting Camera %s to %i'%(Property, val)
        self.internal_state[Property] = val
        self.mmc.setProperty('cam', Property, val)

    @safely
    def STOP(self):
        print 'Stopping Camera....'
        self.mmc.reset()
        self.running = False
