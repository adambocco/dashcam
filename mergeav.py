import subprocess
import os
from os import listdir, getcwd
from os.path import isfile, join, dirname

def file_manager():
    if os.path.exists(str(mypath) + "/temp_video2.avi"):
        os.remove(str(mypath) + "/temp_video2.avi")


mypath = getcwd()
file_manager()
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
logArr = []

with open('avmergelog.txt', 'r') as log:
    for line in log:
        logArr.append(line[:-2].split(','))
        logArr[-1][1] = float(logArr[-1][1])
        logArr[-1][2] = float(logArr[-1][2])

# Get audio files in currect directory
audio_files = []
for f in onlyfiles:
    if (f.split('-')[0] == "DASH0Audio"):
        audio_files.append(f)
    
# Get video files in current directory
video_files = []
for f in onlyfiles:
    if (f.split('-')[0] == "DASH0Video"):
        video_files.append(f)

print("Video files:\n", video_files)
print("\nAudio files: \n", audio_files)

avpairs = []

# Join matching video and audio files
for video_file in video_files: 
    pair = []
    for audio_file in audio_files:
        video_timestamp = video_file.split('-')[1:]
        #remove .avi
        video_timestamp[-1] = video_timestamp[-1][:2]
        audio_timestamp = audio_file.split('-')[1:]
        #remove .wav
        audio_timestamp[-1] = audio_timestamp[-1][:2]
        if ("".join(audio_timestamp) == "".join(video_timestamp)):
            avpairs.append([audio_file, video_file])
            break

for pair in avpairs:
    for entry in logArr:
        print("ENTRY: ",entry)
        if entry[0] == pair[1]:
            pair.append(entry[1:])
print("\nAV Pairs:\n",avpairs)

for log in avpairs:
    recorded_fps = log[2][0]
    audio_filename = log[0]
    video_filename = log[1]
    merged_filename = "DASH0AV-"+("-".join(log[1].split('-')[1:]))
    if abs(recorded_fps - 6) >= 0.01:

        cmd = "ffmpeg -r " + \
            str(recorded_fps) + \
            " -i "+video_filename+" -pix_fmt yuv420p -r 6 temp_video2.avi"
        subprocess.call(cmd, shell=True)

        cmd = "ffmpeg -ac 2 -channel_layout stereo -i "+audio_filename+" -i temp_video2.avi -pix_fmt yuv420p " + merged_filename
        subprocess.call(cmd, shell=True)
        os.remove(str(mypath) + "/temp_video2.avi")

    else:
        cmd = "ffmpeg -ac 2 -channel_layout stereo -i "+audio_filename+" -i "+video_filename+" -pix_fmt yuv420p " + merged_filename
        subprocess.call(cmd, shell=True)
    os.remove(str(mypath) + "/"+audio_filename)
    os.remove(str(mypath) + "/"+video_filename)
    print("Replaced "+audio_filename+" and "+video_filename+" with: \nNEW FILE: "+merged_filename)
    
    
    
