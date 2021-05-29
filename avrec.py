import cv2
import pyaudio
import wave
import threading
import time
import subprocess
import os
from PIL import Image, ImageTk
import tkinter as tk
import argparse
import datetime
import re
import urllib
import RPi.GPIO as GPIO
import picamera
from datetime import datetime

# Necessary command for opencv to use CSI connected camera
if not os.path.exists('/dev/video0'):
    rpistr = "sudo modprobe bcm2835-v4l2"
    p = subprocess.Popen(rpistr, shell=True, preexec_fn=os.setsid)
    time.sleep(1)

BG = "black"
BUTTON_BG = "#eeffee"
BUTTON_ACTIVE_BG="#ccddff"
BUTTON_FONT = ("Helvetica", 17, "bold")

class AudioRecorder():

    # Audio class based on pyAudio and Wave
    def __init__(self, filename):
        self.open = True
        self.rate = 44100
        self.frames_per_buffer = 1024
        self.channels = 2
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
            time.sleep(1)
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            time.sleep(1)
            waveFile = wave.open(self.audio_filename, 'wb')
            waveFile.setnchannels(self.channels)
            waveFile.setsampwidth(self.audio.get_sample_size(self.format))
            waveFile.setframerate(self.rate)
            waveFile.writeframes(b''.join(self.audio_frames)) # Audio write out at this point
            waveFile.close()

        pass

    # Launches the audio recording function using a thread
    def start(self):
        audio_thread = threading.Thread(target=self.record)
        audio_thread.start()


class Application:
    def __init__(self, output_path="./"):
        # Variables set to none are initialized in toggleRecord()
        camindices = find_camera_indices()
        self.cam0Index = camindices[0]
        self.cam1Index = camindices[1]
        self.showVideo = True # Stop rendering in tkinter to improve recording performance
        self.recording0 = False
        self.recording1 = False
        self.frame_counts0 = 1
        self.frame_counts1 = 1
        self.start_time0 = None
        self.start_time1 = None
        self.end_time0 = None
        self.end_time1 = None
        self.loopInterval = 50
        self.defaultScreenText = "Baked\nBeans" # Text on screen when not streaming
        self.curCam = 0 # Currently streaming
        # capture video frames, 0 is your default video camera
        self.vs0 = cv2.VideoCapture(self.cam0Index)
        # "ls /dev/video*" to see available
        self.vs1 = cv2.VideoCapture(self.cam1Index)
        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.out0FileName = None
        self.out1FileName = None
        self.out0 = None
        self.out1 = None
        
        # SPECIFIC TO MY SETUP
        self.vs1.set(cv2.CAP_PROP_BRIGHTNESS, 60)

        self.current_image = None  # current image from the camera
        self.root = tk.Tk()  # initialize root window
        self.root.attributes('-fullscreen', True)  
        self.fullScreenState = False
        self.root.bind("<F11>", self.toggleFullScreen)
        self.root.bind("<Escape>", self.quitFullScreen)
        # These are compatible with 3.5inch 480, 320 display
        w = 480  # width for the Tk root
        h = 320  # height for the Tk root
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
        self.panel.grid(row=0, rowspan=10, column=8,
                        columnspan=25, padx=0, pady=4)

        self.switchBut = tk.Button(self.root, font=BUTTON_FONT,activebackground=BUTTON_ACTIVE_BG,  text="REAR", anchor="w", bg=BUTTON_BG)
        self.switchBut.grid(row=10, column=4, columnspan=5)
        self.switchBut.configure(command=self.switchCam)

        self.botQuit = tk.Button(self.root, font=BUTTON_FONT, text="CLOSE", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG)
        self.botQuit.grid(row=10, column=10)
        self.botQuit.configure(command=self.destructor)

        self.toggleRecordBut0 = tk.Button(self.root,font=BUTTON_FONT, text="REC 0",fg="black", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG)
        self.toggleRecordBut0.grid(row=10, column=16)
        self.toggleRecordBut0.configure(command=lambda:self.toggleRecord(0))

        self.toggleRecordBut1 = tk.Button(self.root,font=BUTTON_FONT, text="REC 1",fg="black", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG)
        self.toggleRecordBut1.grid(row=10, column=22)
        self.toggleRecordBut1.configure(command= lambda:self.toggleRecord(1))

        self.toggleShowVideoBut = tk.Button(self.root,font=BUTTON_FONT, text="HIDE", activebackground=BUTTON_ACTIVE_BG, bg=BUTTON_BG)
        self.toggleShowVideoBut.grid(row=10, column=28)
        self.toggleShowVideoBut.configure(command=self.toggleShowVideo)

        self.video_loop()
        
        
    def toggleFullScreen(self, event):
        self.fullScreenState = not self.fullScreenState
        self.root.attributes("-fullscreen", self.fullScreenState)

    def quitFullScreen(self, event):
        self.fullScreenState = False
        self.root.attributes("-fullscreen", self.fullScreenState)

    def video_loop(self):
        global test
        """ Get frame from the video stream and show it in Tkinter """

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
            self.current_image = Image.fromarray(cv2image)
            self.current_image = self.current_image.resize((480,260), Image.ANTIALIAS) 
            # convert image for tkinter
            imgtk = ImageTk.PhotoImage(image=self.current_image)
            test = cv2image
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.panel.config(image=imgtk, bg=BG)  # show the image
        else:
            self.panel.config(image="",text=self.defaultScreenText, bg="black")

        # call the same function after {self.loopInterval} milliseconds
        self.root.after(self.loopInterval, self.video_loop)

    def toggleShowVideo(self):
        self.showVideo = not self.showVideo
        if (self.showVideo):
            self.toggleShowVideoBut.configure(text="HIDE")
        else:
            self.toggleShowVideoBut.configure(text="SHOW")

    def switchCam(self):
        if self.curCam == 1:
            self.curCam = 0
            self.switchBut.config(text="FRNT")
        else:
            self.curCam = 1
            self.switchBut.config(text="REAR")

    def toggleRecord(self,cam):
        datetimeStamp = datetime.now().strftime("%d-%m-%Y-%H-%M")
        if cam==0:
            if (self.recording0): # Stop recording cam 0
                self.recording0 = False
                audio_thread.stop()
                while threading.active_count() > 1:
                    time.sleep(0.5)
                self.out0.release()
                self.end_time0 = time.time()
                self.recordAVMergeInfo(self.out0FileName, self.frame_counts0, self.start_time0, self.end_time0)
                self.frame_counts0 = 1
                self.toggleRecordBut0.config(text="REC 0", fg="black")
                
            else: # Start recording cam 0
                start_audio_recording("DASH0Audio-"+datetimeStamp)
                self.start_time0 = time.time()
                self.out0FileName = "DASH0Video-"+datetimeStamp+".avi"
                self.out0 = cv2.VideoWriter(self.out0FileName, self.fourcc, 10, (640, 480))
                self.toggleRecordBut0.config(text="STOP 0", fg="red")
                time.sleep(0.5)
                self.recording0 = True
        elif cam==1: 
            if (self.recording1): # Stop recording cam 1
                self.recording1 = False
                self.out1.release()
                self.end_time1 = time.time()
                self.recordAVMergeInfo(self.out1FileName, self.frame_counts1, self.start_time1, self.end_time1)
                self.frame_counts1 = 1
                self.toggleRecordBut1.config(text="REC 1", fg="black")
            else: # Start recording cam 1
                self.start_time1 = time.time()
                self.out1FileName = "DASH1Video-"+datetimeStamp+".avi"
                self.out1 = cv2.VideoWriter(self.out1FileName, self.fourcc, 10, (640, 480))
                self.toggleRecordBut1.config(text="STOP 1", fg="red")
                time.sleep(0.5)
                self.recording1 = True

    def recordAVMergeInfo(self, filename, framecount, start, end):
        t = end-start
        fps = framecount/t
        with open('avmergelog.txt', 'a') as log:
            log.write(f"{filename},{fps},{t}\n")

    def destructor(self):
        try:
            audio_thread.stop()
            while threading.active_count() > 1:
                time.sleep(1)
        except NameError:
            print("No audio thread started")
        self.root.destroy()
        self.vs0.release()  # release web camera 0
        self.vs1.release()  # release web camera 1
        cv2.destroyAllWindows()  # it is not mandatory in this application



def start_audio_recording(filename):
    global audio_thread
    audio_thread = AudioRecorder(filename)
    audio_thread.start()
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
