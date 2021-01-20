# Created i La Selva 18-mars-04 15:15
# Modified i La Selva 19-Januari-04  20:19

from PIL import Image, ImageTk
import Tkinter as tk
import argparse
import time
import datetime
import cv2
import os
import re
import subprocess
import urllib
import RPi.GPIO as GPIO
import threading
import picamera

# initialise pi camera v4l2
if not os.path.exists('/dev/video0'):
   rpistr = "sudo modprobe bcm2835-v4l2"
   p = subprocess.Popen(rpistr, shell=True, preexec_fn=os.setsid)
   time.sleep(1)
   
def do_picamera(app):
    camera = picamera.PiCamera()
    #camera.awb_mode = 'auto'
    camera.brightness = 50
    #camera.rotation= 90
    camera.resolution = (2592, 1944)
    data = time.strftime("%Y-%b-%d_(%H%M%S)")
    texte = "picture take:" + data
    camera.start_preview()
    camera.capture('%s.jpg' % data)
    camera.stop_preview()

    
class Application:
    def __init__(self, output_path = "./"):
        """ Initialize application which uses OpenCV + Tkinter. It displays
            a video stream in a Tkinter window and stores current snapshot on disk """
        self.vs = cv2.VideoCapture(0) # capture video frames, 0 is your default video camera
        self.output_path = output_path  # store output path
        self.current_image = None  # current image from the camera
        self.root = tk.Tk()  # initialize root window
        defaultbg = self.root.cget('bg') # set de default grey color to use in labels background
        w = 650 # width for the Tk root
        h = 550 # height for the Tk root
        self.root .resizable(0, 0)
        ws = self.root .winfo_screenwidth() # width of the screen
        hs = self.root .winfo_screenheight() # height of the screen
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root .geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.root.title("     LA  SELVA - SAFETY CONTROL UNIT     ")  # set window title
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)

        self.panel = tk.Label(self.root)  # initialize image panel
        self.panel.grid(row=0, rowspan=10, column=8, columnspan=25, padx=4, pady=6)

        self.botShoot2 = tk.Button(self.root,width=18, font=('arial', 14, 'normal'),  text="PICAM-SHOOT" ,anchor="w")
        self.botShoot2.grid(row=10, column=20,columnspan=6)
        self.botShoot2.configure(command=self.picam)        

        self.botShoot1= tk.Button(self.root,width=10, font=('arial', 14, 'normal'),  text="CV2-SHOOT" ,anchor="w")
        self.botShoot1.grid(row=10, column=26,columnspan=5)
        self.botShoot1.configure(command=self.snapshot)

        
        self.botQuit = tk.Button(self.root,width=6,font=('arial narrow', 14, 'normal'), text="CLOSE", activebackground="#00dfdf")
        self.botQuit.grid(row=10,column=32)
        self.botQuit.configure(command=self.destructor)        
                
        self.video_loop()
        
    def video_loop(self):
        global test
        """ Get frame from the video stream and show it in Tkinter """
        ok, frame = self.vs.read()  # read frame from video stream
        if ok:  # frame captured without any errors
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)  # convert colors from BGR to RGBA
            self.current_image = Image.fromarray(cv2image)  # convert image for PIL
            imgtk = ImageTk.PhotoImage(image=self.current_image)  # convert image for tkinter
            test = cv2image
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.panel.config(image=imgtk)  # show the image
        self.root.after(30, self.video_loop)  # call the same function after 30 milliseconds

    def snapshot(self):
        imageName = str(time.strftime("%Y-%m-%d %H_%M")) + '.jpg'
        cv2.imwrite(imageName,test)

    def picam(self):
        self.vs.release()
        t = threading.Thread(target=do_picamera, args=(self,))
        t.start()
        
    def destructor(self):
        self.root.destroy()
        self.vs.release()  # release web camera
        cv2.destroyAllWindows()  # it is not mandatory in this application

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", default="./Pictures",
help="path to output directory to store snapshots (default: current folder")
args = vars(ap.parse_args())

# start the app
pba = Application(args["output"])
pba.root.mainloop()







