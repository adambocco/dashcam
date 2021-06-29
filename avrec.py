import cv2
from pyaudio import PyAudio
import wave
import threading
import time
import subprocess
import os
import sys
from PIL import Image, ImageTk
import tkinter as tk
import argparse
import datetime
import re
import urllib
from picamera import PiCamera
import imutils
from datetime import datetime
import RPi.GPIO as GPIO

from audioRecorder import AudioRecorder

MAIN_WINDOW_GEOMETRY = '1280x720'
DATE_FORMAT = "%d-%m-%Y-%H-%M"

BG = "black"
BUTTON_BG = "#eeffee"
BUTTON_ACTIVE_BG="#ccddff"
BUTTON_FONT = ("Helvetica", 10, "bold")
LABEL_FONT = ("Cascadia Mono", 10, "bold")
BTN_HEIGHT = 1

RECORD_FRONT_PIN = 17
RECORD_REAR_PIN = 27
ENABLE_SHOW_PIN = 22
TOGGLE_SHOW_PIN = 23
OTHER_PIN = 24

def setupGPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RECORD_FRONT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(RECORD_REAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(ENABLE_SHOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(TOGGLE_SHOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(OTHER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)




# Necessary command for opencv to use CSI connected camera
if not os.path.exists('/dev/video0'):
    rpistr = "sudo modprobe bcm2835-v4l2"
    p = subprocess.Popen(rpistr, shell=True, preexec_fn=os.setsid)
    time.sleep(1)



class Application:
    def __init__(self, output_path="./"):
        # Variables set to none are initialized in toggleRecord()
        camindices = find_camera_indices()
        self.camIndexUSB = camindices[0]

        self.picam = PiCamera()
        self.showVideo = True # Stop rendering in tkinter to improve recording performance

        self.recordingPiCam = False
        self.recordingUSB = False

        self.frameCountsUSB = 1

        self.startTimeUSB = None
        self.endTimeUSB = None

        self.loopInterval = 20

        self.curCam = 0 # Currently streaming
        # capture video frames, 0 is your default video camera
        self.streamUSB = cv2.VideoCapture(self.camIndexUSB)

        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.outFileNamePiCam = None
        self.outFileNameUSB = None
        self.outPiCam = None
        self.outUSB = None
        
        self.streamUSB.set(cv2.CAP_PROP_BRIGHTNESS,50)

        self.current_image = None  # current image from the camera
        self.root = tk.Tk()  # initialize root window
        self.fullScreenState = True
        self.root.attributes('-fullscreen', self.fullScreenState)  
        self.root.bind("<F11>", self.toggleFullScreen)
        self.root.bind("<Escape>", self.quitFullScreen)
        # These are compatible with 3.5inch 480, 320 display

        self.root.resizable(0, 0)
        # w = self.root .winfo_screenwidth()  # width of the screen
        # h = self.root .winfo_screenheight()  # height of the screen

        self.root.geometry(MAIN_WINDOW_GEOMETRY)
        # set window title
        self.root.title("DASHCAM")
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)
        self.root.config(bg=BG)

        self.panel = tk.Label(self.root, bg=BG)  # initialize image panel
        self.panel.grid(row=1, column=0, columnspan=6)

        self.recordingLock = False
        self.readGPIO = True

        self.botQuit = tk.Button(self.root, font=BUTTON_FONT, text="EXIT", bg="#ffafaf", activebackground=BUTTON_ACTIVE_BG,height=BTN_HEIGHT, command=self.destructor)
        self.botQuit.grid(row=0, column=0)

        self.recordingLabelUSB = tk.Label(self.root, bg="black", fg="white", font=LABEL_FONT, text="REC FRONT" if GPIO.input(RECORD_FRONT_PIN)==GPIO.HIGH else "")
        self.recordingLabelUSB.grid(row=0, column=1)

        self.recordingLabelPiCam = tk.Label(self.root, bg="black", fg="white", font=LABEL_FONT, text="REC REAR" if GPIO.input(RECORD_REAR_PIN)==GPIO.HIGH else "")
        self.recordingLabelPiCam.grid(row=0, column=2)

        self.enableShowLabel = tk.Label(self.root, bg="black", fg="white", font=LABEL_FONT, text="SHOWING" if GPIO.input(ENABLE_SHOW_PIN)==GPIO.HIGH else "")
        self.enableShowLabel.grid(row=0, column=3)

        self.toggleShowLabel = tk.Label(self.root, bg="black", fg="white", font=LABEL_FONT, text="REAR" if GPIO.input(TOGGLE_SHOW_PIN)==GPIO.HIGH else "FRONT")
        self.toggleShowLabel.grid(row=0, column=4)

        self.gpioThread = threading.Thread(target=self.handleToggleSwitches, args=())
        self.gpioThread.start()

        self.root.after(self.loopInterval, self.videoLoopUSB)
        
    def toggleFullScreen(self, event):
        self.fullScreenState = not self.fullScreenState
        self.root.attributes("-fullscreen", self.fullScreenState)

    def quitFullScreen(self, event):
        self.fullScreenState = False
        self.root.attributes("-fullscreen", self.fullScreenState)


    def videoLoopUSB(self):

        frameOK, frame = self.streamUSB.read()  # read frame from video stream

        if not self.recordingLock:

            if frameOK and self.recordingUSB:
                self.frameCountsUSB += 1
                self.outUSB.write(frame)

        if self.showVideo and frameOK and self.curCam == 1:

            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            cv2image = imutils.resize(cv2image, height=700)

            imgtk = ImageTk.PhotoImage(image=Image.fromarray(cv2image))
            self.panel.config(image=imgtk) 
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            
        # call the same function after {self.loopInterval} milliseconds
        self.root.after(self.loopInterval, self.videoLoopUSB)


    def toggleRecordUSB(self):
        self.recordingLock = True

        self.recordingUSB = not self.recordingUSB
        if not self.recordingUSB: # Stop recording cam 0
            audioDuration = self.audio_thread.stop()
            time.sleep(1)
            self.endTimeUSB = time.time()
            self.outUSB.release()
            self.recordAVMergeInfo(self.outFileNameUSB, self.frameCountsUSB, self.startTimeUSB, self.endTimeUSB, audioDuration)
            self.frameCountsUSB = 1
            
        else: # Start recording cam 0
            datetimeStamp = datetime.now().strftime(DATE_FORMAT)
            self.start_audio_recording("./DASH0-Audio/"+datetimeStamp)
            self.startTimeUSB = time.time()
            self.outFileNameUSB = "./DASH0-Video/"+datetimeStamp+".avi"
            self.outUSB = cv2.VideoWriter(self.outFileNameUSB, self.fourcc, 10, (640, 480))
            time.sleep(0.5)

        self.recordingLock = False            


    def toggleRecordPiCam(self):
        self.recordingPiCam = not self.recordingPiCam

        if self.recordingPiCam:
            datetimeStamp = datetime.now().strftime(DATE_FORMAT)
            self.outFileNamePiCam = "/home/pi/Desktop/dashcam/DASH1-Video/"+datetimeStamp+".h264"
            self.picam.start_recording(self.outFileNamePiCam)
        else:
            self.picam.stop_recording()


    def recordAVMergeInfo(self, filename, framecount, start, end, audioDuration):
        t = end-start
        fps = framecount/t
        with open('avmergelog.txt', 'a') as log:
            log.write(f"{filename},{fps},{t}, {audioDuration}\n")


    def destructor(self):
        self.readGPIO = False
        
        try:
            if self.recordingUSB: # Stop recording cam 0
                self.recordingUSB = False
                audioDuration = self.audio_thread.stop()
                self.endTimeUSB = time.time()
                while self.audio_thread.audio_thread.is_alive():
                    self.endTimeUSB = time.time()
                    time.sleep(0.5)
                self.outUSB.release()

                self.recordAVMergeInfo(self.outFileNameUSB, self.frameCountsUSB, self.startTimeUSB, self.endTimeUSB, audioDuration)
            if (self.recordingPiCam): # Stop recording cam 1
                self.picam.stop_recording()
            
            GPIO.cleanup()
            self.root.destroy()
            self.streamUSB.release()  # release web camera 0
            self.picam.close()
            cv2.destroyAllWindows()  # it is not mandatory in this application
            exit()
        except:
            exit()

    def start_audio_recording(self, filename):
        self.audio_thread = AudioRecorder(filename)
        self.audio_thread.start()
        return


    def handleToggleSwitches(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RECORD_FRONT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(RECORD_REAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(ENABLE_SHOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(TOGGLE_SHOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(OTHER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        from messages import cuteMessages
        cmLength = len(cuteMessages)
        cmIndex = 0

        while self.readGPIO:
            if (GPIO.input(RECORD_FRONT_PIN) == GPIO.LOW) == self.recordingUSB:
                print("RECORD FRONT CHANGED: ",self.recordingUSB)
                self.toggleRecordUSB()
                self.recordingLabelUSB.config(text="REC FRONT" if self.recordingUSB else "")


            if (GPIO.input(RECORD_REAR_PIN) == GPIO.LOW) == self.recordingPiCam:
                print("RECORD REAR CHANGED: ",self.recordingPiCam)
                self.toggleRecordPiCam()
                self.recordingLabelPiCam.config(text="REC REAR" if self.recordingPiCam else "")

            if (GPIO.input(ENABLE_SHOW_PIN) == GPIO.LOW) == self.showVideo:
                print("SHOW VIDEO: ",self.showVideo)
                self.showVideo = not self.showVideo

                self.enableShowLabel.config(text="SHOWING" if self.showVideo else "")

                if self.showVideo:
                    self.handlePiCamera()
                    cmIndex += 1
                    if cmIndex > cmLength:
                        cmIndex = 0
                else:
                    if cmLength == cmIndex:
                        im = Image.open('./gabby1.jpg')
                        im = im.resize((1280, 720))
                        im = im.rotate(280)
                        img = ImageTk.PhotoImage(im)
                        self.panel.config(image=img, bg="black")
                    else:   
                        self.panel.config(image='', bg="black", fg="white", font=('Helvetica', 30), text=makeLineBreaks(cuteMessages[cmIndex],30))
                    self.picam.stop_preview()

            if (GPIO.input(TOGGLE_SHOW_PIN) == GPIO.HIGH) == (self.curCam == 1):
                print("RECORD FRONT CHANGED: ",self.curCam)
                self.curCam = 0 if self.curCam == 1 else 1
                self.handlePiCamera()

                self.toggleShowLabel.config(text="REAR" if self.curCam == 1 else "FRONT")

    def handlePiCamera(self):
        if self.curCam == 0 and self.showVideo:
            self.picamThread = threading.Thread(target=self.startPiCameraPreview, args=())
            self.picamThread.start()
        elif self.curCam == 1:
            try:
                self.picam.stop_preview()
            except:
                print("Can't stop preview")

    def startPiCameraPreview(self):
        self.picam.start_preview(fullscreen=False, window=(-20, 30, 1330, 690))
    

def find_camera_indices():
    valid_cams = []
    for i in range(8):
        cap = cv2.VideoCapture(i)
        if cap is None or not cap.isOpened():
            pass
        else:
            valid_cams.append(i)
    return valid_cams
    

def makeLineBreaks(stringToBreak, breakIndex):
    strBuilder = ""
    ret = ""
    strArr = stringToBreak.split(' ')
    for word in strArr:
        if len(strBuilder) + len(word) > breakIndex:
            ret += strBuilder + "\n"
            strBuilder = word + " "
        else:
            strBuilder += word + " "
    ret += strBuilder
    return ret

    

if __name__ == "__main__":
    pba = Application()
    pba.root.mainloop()
    exit()
