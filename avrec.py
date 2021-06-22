import cv2
import pyaudio
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
import RPi.GPIO as GPIO
import picamera
import imutils
from datetime import datetime
import RPi.GPIO as GPIO

BG = "black"
BUTTON_BG = "#eeffee"
BUTTON_ACTIVE_BG="#ccddff"
BUTTON_FONT = ("Helvetica", 10, "bold")
LABEL_FONT = ("Helvetica", 10, "bold")
BTN_HEIGHT = 1

RECORD_FRONT_PIN = 17
RECORD_REAR_PIN = 27
ENABLE_SHOW_PIN = 22
TOGGLE_SHOW_PIN = 23

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RECORD_FRONT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RECORD_REAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(ENABLE_SHOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(TOGGLE_SHOW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)




# Necessary command for opencv to use CSI connected camera
if not os.path.exists('/dev/video0'):
    rpistr = "sudo modprobe bcm2835-v4l2"
    p = subprocess.Popen(rpistr, shell=True, preexec_fn=os.setsid)
    time.sleep(1)

class AudioRecorder():

    # Audio class based on pyAudio and Wave
    def __init__(self, filename):
        self.open = True
        self.rate = 44100
        self.frames_per_buffer = 1024
        self.channels = 2
        self.startTime = 0
        self.endTime = 0
        self.duration = 0
        self.format = pyaudio.paInt16
        self.audio_filename = filename+".wav"
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer=self.frames_per_buffer)
        self.audio_frames = []

    # Audio starts being recorded in separate thread

    def record(self):

        self.stream.start_stream()
        while(self.open == True):
            data = self.stream.read(self.frames_per_buffer)
            self.audio_frames.append(data)
            if self.open == False:
                break

    # Finishes the audio recording therefore the thread too

    def stop(self):

        if self.open == True:
            self.open = False
            try:
                self.audio_thread.join()
            except:
                pass
            time.sleep(1)
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            self.endTime = time.time()
            self.duration = self.endTime - self.startTime
            time.sleep(1)
            waveFile = wave.open(self.audio_filename, 'wb')
            waveFile.setnchannels(self.channels)
            waveFile.setsampwidth(self.audio.get_sample_size(self.format))
            waveFile.setframerate(self.rate)
            waveFile.writeframes(b''.join(self.audio_frames)) # Audio write out at this point
            waveFile.close()
        return self.duration

    # Launches the audio recording function using a thread
    def start(self):
        self.startTime = time.time()
        self.audio_thread = threading.Thread(target=self.record)
        self.audio_thread.start()


class Application:
    def __init__(self, output_path="./"):
        # Variables set to none are initialized in toggleRecord()
        camindices = find_camera_indices()
        self.cam0Index = camindices[1]
        self.cam1Index = camindices[0]
        self.showVideo = True # Stop rendering in tkinter to improve recording performance
        self.recording0 = False
        self.recording1 = False
        self.frame_counts0 = 1
        self.frame_counts1 = 1
        self.start_time0 = None
        self.start_time1 = None
        self.end_time0 = None
        self.end_time1 = None
        self.loopInterval = 15
        self.defaultScreenText = "Baked\nBeans" # Text on screen when not streaming
        self.curCam = 1 # Currently streaming
        # capture video frames, 0 is your default video camera
        self.vs0 = cv2.VideoCapture(self.cam0Index)
        # "ls /dev/video*" to see available
        self.vs1 = cv2.VideoCapture(self.cam1Index)
        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.out0FileName = None
        self.out1FileName = None
        self.out0 = None
        self.out1 = None
        
        self.vs0.set(cv2.CAP_PROP_BRIGHTNESS,70)
        
        self.vs1.set(cv2.CAP_PROP_BRIGHTNESS, 70)

        self.current_image = None  # current image from the camera
        self.root = tk.Tk()  # initialize root window
        self.root.attributes('-fullscreen', True)  
        self.fullScreenState = False
        self.root.bind("<F11>", self.toggleFullScreen)
        self.root.bind("<Escape>", self.quitFullScreen)
        # These are compatible with 3.5inch 480, 320 display
        w = 1024  # width for the Tk root
        h = 720  # height for the Tk root
        self.root.resizable(0, 0)
        ws = self.root .winfo_screenwidth()  # width of the screen
        hs = self.root .winfo_screenheight()  # height of the screen
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root .geometry('%dx%d+%d+%d' % (w, h, x, y))
        # set window title
        self.root.title("DASHCAM")
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)
        self.root.config(bg=BG)

        self.panel = tk.Label(self.root, bg=BG)  # initialize image panel
        self.panel.grid(row=1, column=0, columnspan=6)

        self.botQuit = tk.Button(self.root, font=BUTTON_FONT, text="EXIT", bg="#ffafaf", activebackground=BUTTON_ACTIVE_BG,height=BTN_HEIGHT)
        self.botQuit.grid(row=0, column=0)
        self.botQuit.configure(command=self.destructor)

        self.recording0Label = tk.Label(self.root, bg="#3f4a5b", fg="white", font=LABEL_FONT, text="REC FRONT" if GPIO.input(RECORD_FRONT_PIN)==GPIO.HIGH else "")
        self.recording0Label.grid(row=0, column=1)

        self.recording1Label = tk.Label(self.root, bg="#3f4a5b", fg="white", font=LABEL_FONT, text="REC REAR" if GPIO.input(RECORD_REAR_PIN)==GPIO.HIGH else "")
        self.recording1Label.grid(row=0, column=2)

        self.enableShowLabel = tk.Label(self.root, bg="#3f4a5b", fg="white", font=LABEL_FONT, text="SHOWING" if GPIO.input(ENABLE_SHOW_PIN)==GPIO.HIGH else "")
        self.enableShowLabel.grid(row=0, column=3)

        self.toggleShowLabel = tk.Label(self.root, bg="#3f4a5b", fg="white", font=LABEL_FONT, text="REAR" if GPIO.input(TOGGLE_SHOW_PIN)==GPIO.HIGH else "FRONT")
        self.toggleShowLabel.grid(row=0, column=4)


        # self.switchBut = tk.Button(self.root, font=BUTTON_FONT,activebackground=BUTTON_ACTIVE_BG,  text="REAR", anchor="w", bg=BUTTON_BG,height=BTN_HEIGHT)
        # self.switchBut.grid(row=1, column=0)
        # self.switchBut.configure(command=self.switchCam)

        # self.toggleRecordBut0 = tk.Button(self.root,font=BUTTON_FONT, text="REC 0",fg="black", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG,height=BTN_HEIGHT)
        # self.toggleRecordBut0.grid(row=2, column=0)
        # self.toggleRecordBut0.configure(command=lambda:self.toggleRecord(0))

        # self.toggleRecordBut1 = tk.Button(self.root,font=BUTTON_FONT, text="REC 1",fg="black", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG,height=BTN_HEIGHT)
        # self.toggleRecordBut1.grid(row=3, column=0)
        # self.toggleRecordBut1.configure(command= lambda:self.toggleRecord(1))

        # self.toggleShowVideoBut = tk.Button(self.root,font=BUTTON_FONT, text="HIDE", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG,height=BTN_HEIGHT)
        # self.toggleShowVideoBut.grid(row=4, column=0)
        # self.toggleShowVideoBut.configure(command=self.toggleShowVideo)

        # self.video_loop()
        self.thr = threading.Thread(target=self.video_loop, args=())
        self.thr.start()
        
        
    def toggleFullScreen(self, event):
        self.fullScreenState = not self.fullScreenState
        self.root.attributes("-fullscreen", self.fullScreenState)

    def quitFullScreen(self, event):
        self.fullScreenState = False
        self.root.attributes("-fullscreen", self.fullScreenState)

    def video_loop(self):
        while True:
            """ Get frame from the video stream and show it in Tkinter """

            self.handleToggleSwitches()

            ok0, frame0 = self.vs0.read()  # read frame from video stream
            ok1, frame1 = self.vs1.read()  # read frame from video stream
            shownFrame = frame0 if self.curCam == 0 else frame1
            shownOk = ok0 if self.curCam == 0 else ok1
            if ok0 and self.recording0:  # frame captured without any errors
                self.frame_counts0 += 1
                self.out0.write(frame0)
            if ok1 and self.recording1:
                self.frame_counts1 += 1
                self.out1.write(frame1)
            if self.showVideo and shownOk:
                # convert colors from BGR to RGBA
                cv2image = cv2.cvtColor(shownFrame, cv2.COLOR_BGR2RGBA)
                cv2image = imutils.resize(cv2image, width=1024)

                # convert image for tkinter
                imgtk = ImageTk.PhotoImage(image=Image.fromarray(cv2image))
                self.panel.config(image=imgtk, bg=BG)  # show the image
                self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
        
        # call the same function after {self.loopInterval} milliseconds
        # self.root.after(self.loopInterval, self.video_loop)

    def handleToggleSwitches(self):
        if (GPIO.input(RECORD_FRONT_PIN) == GPIO.LOW) == self.recording0:
            print("RECORD FRONT CHANGED: ",self.recording0)
            self.toggleRecord(0)
            self.recording0 = not self.recording0
            self.recording0Label.config(text="REC FRONT" if self.recording0 else "")


        if (GPIO.input(RECORD_REAR_PIN) == GPIO.LOW) == self.recording1:
            print("RECORD REAR CHANGED: ",self.recording1)
            self.toggleRecord(1)
            self.recording1 = not self.recording1
            self.recording1Label.config(text="REC REAR" if self.recording1 else "")


        if (GPIO.input(ENABLE_SHOW_PIN) == GPIO.LOW) == self.showVideo:
            print("SHOW VIDEO: ",self.showVideo)
            self.showVideo = not self.showVideo
            self.enableShowLabel.config(text="SHOWING" if self.showVideo else "")

        if (GPIO.input(TOGGLE_SHOW_PIN) == GPIO.HIGH) == (self.curCam == 1):
            print("RECORD FRONT CHANGED: ",self.curCam)
            self.curCam = 0 if self.curCam == 1 else 1
            self.toggleShowLabel.config(text="REAR" if self.curCam == 1 else "FRONT")


    def toggleRecord(self,cam):
        datetimeStamp = datetime.now().strftime("%d-%m-%Y-%H-%M")
        if cam==0:
            if (self.recording0): # Stop recording cam 0
                audioDuration = self.audio_thread.stop()
                while threading.active_count() > 2:
                    time.sleep(0.5)
                self.out0.release()
                self.end_time0 = time.time()
                self.recordAVMergeInfo(self.out0FileName, self.frame_counts0, self.start_time0, self.end_time0, audioDuration)
                self.frame_counts0 = 1
                
            else: # Start recording cam 0
                self.start_audio_recording("./DASH0-Audio/"+datetimeStamp)
                self.start_time0 = time.time()
                self.out0FileName = "./DASH0-Video/"+datetimeStamp+".avi"
                self.out0 = cv2.VideoWriter(self.out0FileName, self.fourcc, 10, (640, 480))
                time.sleep(0.5)
        elif cam==1: 
            if (self.recording1): # Stop recording cam 1
                self.out1.release()
                self.end_time1 = time.time()
                self.recordAVMergeInfo(self.out1FileName, self.frame_counts1, self.start_time1, self.end_time1, 0)
                self.frame_counts1 = 1
            else: # Start recording cam 1
                self.start_time1 = time.time()
                self.out1FileName = "./DASH1-Video/"+datetimeStamp+".avi"
                self.out1 = cv2.VideoWriter(self.out1FileName, self.fourcc, 10, (640, 480))
                time.sleep(0.5)


    def recordAVMergeInfo(self, filename, framecount, start, end, audioDuration):
        t = end-start
        fps = framecount/t
        with open('avmergelog.txt', 'a') as log:
            log.write(f"{filename},{fps},{t}, {audioDuration}\n")

    def destructor(self):

        GPIO.cleanup()
        
        if (self.recording0): # Stop recording cam 0
            self.recording0 = False
            audioDuration = self.audio_thread.stop()
            self.end_time0 = time.time()
            while threading.active_count() > 1:
                time.sleep(0.5)
                self.end_time0 = time.time()
            self.out0.release()

            self.recordAVMergeInfo(self.out0FileName, self.frame_counts0, self.start_time0, self.end_time0, audioDuration)
        if (self.recording1): # Stop recording cam 1
            self.recording1 = False
            self.out1.release()
            self.end_time1 = time.time()
            self.recordAVMergeInfo(self.out1FileName, self.frame_counts1, self.start_time1, self.end_time1, 0)

        try:
            self.audio_thread.stop()

        except (NameError, AttributeError) as e:
            print("No audio thread started")
        
        self.root.destroy()
        self.vs0.release()  # release web camera 0
        self.vs1.release()  # release web camera 1
        cv2.destroyAllWindows()  # it is not mandatory in this application
        exit()


    def start_audio_recording(self, filename):
        self.audio_thread = AudioRecorder(filename)
        print("Audio thread: ",self.audio_thread)
        print("Audio thread type: ", type(self.audio_thread))
        self.audio_thread.start()
        return
    

def find_camera_indices():
    valid_cams = []
    for i in range(8):
        cap = cv2.VideoCapture(i)
        if cap is None or not cap.isOpened():
            pass
        else:
            valid_cams.append(i)
    return valid_cams


if __name__ == "__main__":
    pba = Application()
    pba.root.mainloop()
