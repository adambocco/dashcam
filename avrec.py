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
        self.format = pyaudio.paInt16
        self.audio_filename = filename+".wav"
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer=self.frames_per_buffer)
        self.audio_frames = []

    # Audio starts being recorded

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
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()

            waveFile = wave.open(self.audio_filename, 'wb')
            waveFile.setnchannels(self.channels)
            waveFile.setsampwidth(self.audio.get_sample_size(self.format))
            waveFile.setframerate(self.rate)
            waveFile.writeframes(b''.join(self.audio_frames))
            waveFile.close()

        pass

    # Launches the audio recording function using a thread
    def start(self):
        audio_thread = threading.Thread(target=self.record)
        audio_thread.start()


class Application:
    def __init__(self, output_path="./"):
        """ Initialize application which uses OpenCV + Tkinter. It displays
            a video stream in a Tkinter window and stores current snapshot on disk """

        
        self.recording0 = False
        self.recording1 = False
        self.frame_counts0 = 1
        self.frame_counts1 = 1
        self.start_time0 = None
        self.start_time1 = None
        self.end_time0 = None
        self.end_time1 = None

        self.curCam = 0
        # capture video frames, 0 is your default video camera
        self.vs0 = cv2.VideoCapture(0)
        # capture video frames, 0 is your default video camera
        self.vs1 = cv2.VideoCapture(2)
        self.fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.out0FileName = None
        self.out1FileName = None
        self.out0SaveName = "DASH0.avi"
        self.out1SaveName = "DASH1.avi"
        self.out0 = None
        self.out1 = None

        self.current_image = None  # current image from the camera
        self.root = tk.Tk()  # initialize root window
        # set de default grey color to use in labels background
        defaultbg = self.root.cget('bg')
        w = 650  # width for the Tk root
        h = 550  # height for the Tk root
        self.root .resizable(0, 0)
        ws = self.root .winfo_screenwidth()  # width of the screen
        hs = self.root .winfo_screenheight()  # height of the screen
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root .geometry('%dx%d+%d+%d' % (w, h, x, y))
        # set window title
        self.root.title("     LA  SELVA - SAFETY CONTROL UNIT     ")
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)

        self.panel = tk.Label(self.root)  # initialize image panel
        self.panel.grid(row=0, rowspan=10, column=8,
                        columnspan=25, padx=4, pady=6)

        self.switchBut = tk.Button(self.root, width=10, font=(
            'arial', 14, 'normal'),  text="SWITCH", anchor="w")
        self.switchBut.grid(row=10, column=4, columnspan=5)
        self.switchBut.configure(command=self.switchCam)

        self.botQuit = tk.Button(self.root, width=6, font=(
            'arial narrow', 14, 'normal'), text="CLOSE", activebackground="#00dfdf")
        self.botQuit.grid(row=10, column=10)
        self.botQuit.configure(command=self.destructor)

        self.toggleRecordBut0 = tk.Button(self.root, width=6, text="Record 2",fg="black")
        self.toggleRecordBut0.grid(row=10, column=16)
        self.toggleRecordBut0.configure(command=lambda:self.toggleRecord(0))

        self.toggleRecordBut1 = tk.Button(self.root, width=6, text="Record 1",fg="black")
        self.toggleRecordBut1.grid(row=10, column=22)
        self.toggleRecordBut1.configure(command= lambda:self.toggleRecord(1))

        self.video_loop()

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
        if shownOk:
            # convert colors from BGR to RGBA
            cv2image = cv2.cvtColor(shownFrame, cv2.COLOR_BGR2RGBA)
            self.current_image = Image.fromarray(
                cv2image)  # convert image for PIL
            # convert image for tkinter
            imgtk = ImageTk.PhotoImage(image=self.current_image)
            test = cv2image
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.panel.config(image=imgtk)  # show the image

        # call the same function after 30 milliseconds
        self.root.after(30, self.video_loop)

    def switchCam(self):
        self.curCam = 0 if self.curCam == 1 else 1

    def toggleRecord(self,cam):
        datetimeStamp = datetime.now().strftime("%d-%m-%Y-%H-%M")
        if cam==0:
            if (self.recording0):
                self.recording0 = False
                audio_thread.stop()
                self.out0.release()
                self.frame_counts0
                self.end_time0 = time.time()
                self.recordAVMergeInfo()
                self.toggleRecordBut0.config(text="Record 0", fg="black")
                
            else:
                start_audio_recording("DASH0Audio-"+datetimeStamp)
                self.start_time0 = time.time()
                self.out0FileName = "DASH0Video-"+datetime.stamp+".avi"
                self.out0 = cv2.VideoWriter(self.out0FileName, self.fourcc, 10, (640, 480))
                self.toggleRecordBut0.config(text="Recording 0", fg="red")
                time.sleep(0.5)
                self.recording0 = True
        elif cam==1:
            if (self.recording1):
                self.recording1 = False
                audio_thread.stop()
                self.out1.release()
                self.frame_counts1
                self.end_time1 = time.time()
                self.recordAVMergeInfo()
                self.toggleRecordBut1.config(text="Record 1", fg="black")
            else:
                start_audio_recording("DASH1Audio-"+datetimeStamp)
                self.start_time1 = time.time()
                self.out1FileName = "DASH1Video-"+datetimeStamp+".avi"
                self.out1 = cv2.VideoWriter(self.out1FileName, self.fourcc, 10, (640, 480))
                self.toggleRecordBut1.config(text="Recording 1", fg="red")
                time.sleep(0.5)
                self.recording1 = True

    def recordAVMergeInfo(self):
        pass
        # TODO: log fps to file to merge A/V later

    def destructor(self):
        audio_thread.stop()
        while threading.active_count() > 1:
            time.sleep(1)
        stop_AVrecording(self.out0FileName, self.out0SaveName, self.start_time0, self.frame_counts0)
        stop_AVrecording(self.out1FileName, self.out1SaveName, self.start_time1, self.frame_counts1)
        self.root.destroy()
        self.vs0.release()  # release web camera
        self.vs1.release()  # release web camera
        cv2.destroyAllWindows()  # it is not mandatory in this application



def start_audio_recording(filename):
    global audio_thread
    audio_thread = AudioRecorder(filename)
    audio_thread.start()
    return


def stop_AVrecording(filename, savename, start_time, frame_counts):
    local_path = os.getcwd()
    elapsed_time = time.time() - start_time
    recorded_fps = frame_counts / elapsed_time
    print("total frames " + str(frame_counts))
    print("elapsed time " + str(elapsed_time))
    print("recorded fps " + str(recorded_fps))

#     # Makes sure the threads have finished


# #	 Merging audio and video signal

#     # If the fps rate was higher/lower than expected, re-encode it to the expected
#     if abs(recorded_fps - 6) >= 0.01:

#         cmd = "ffmpeg -r " + \
#             str(recorded_fps) + \
#             " -i "+filename+" -pix_fmt yuv420p -r 6 temp_video2.avi"
#         subprocess.call(cmd, shell=True)

#         cmd = "ffmpeg -ac 2 -channel_layout stereo -i temp_audio.wav -i temp_video2.avi -pix_fmt yuv420p " + savename
#         subprocess.call(cmd, shell=True)
#         os.remove(str(local_path) + "/temp_video2.avi")

#     else:
#         cmd = "ffmpeg -ac 2 -channel_layout stereo -i temp_audio.wav -i "+filename+" -pix_fmt yuv420p " + savename
#         subprocess.call(cmd, shell=True)


# Required and wanted processing of final files
def file_manager(filenames):

    local_path = os.getcwd()

    if os.path.exists(str(local_path) + "/temp_audio.wav"):
        os.remove(str(local_path) + "/temp_audio.wav")

    if os.path.exists(str(local_path) + "/temp_video.avi"):
        os.remove(str(local_path) + "/temp_video.avi")

    if os.path.exists(str(local_path) + "/temp_video2.avi"):
        os.remove(str(local_path) + "/temp_video2.avi")

    for filename in filenames:
        if os.path.exists(str(local_path) + "/" + filename + ".avi"):
            os.remove(str(local_path) + "/" + filename + ".avi")


if __name__ == "__main__":
    filenames = ["DASH0temp.avi", "DASH1temp.avi", "DASH0.avi", "DASH1.avi"]
    file_manager(filenames)
    start_audio_recording()
    pba = Application()
    pba.root.mainloop()
