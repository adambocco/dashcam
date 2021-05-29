import subprocess
import os
from os import listdir, getcwd
from os.path import isfile, join, dirname

def file_manager():
    if os.path.exists(str(mypath) + "/temp_video2.avi"):
        os.remove(str(mypath) + "/temp_video2.avi")


mypath = getcwd()
file_manager()
audio_files = [f.split(".")[0] for f in listdir(mypath+"/DASH0-Audio") ]
video_files = [f.split(".")[0] for f in listdir(mypath+"/DASH0-Video") ]
merged_files = [f.split(".")[0] for f in listdir(mypath+"/AV") ]

timestamps = []


def getLength(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)


with open('avmergelog.txt', 'r') as log:
    for line in log:
        lineArr = line[:-2].split(',')
        timestamp = lineArr[0].split("/")[-1].split(".")[0]
        print("Timestamp: ",timestamp)
        print("Merged files: ", merged_files)
        print("Video files: ", video_files)
        print("Audio files: ", audio_files)
        
        if timestamp not in merged_files and timestamp in video_files and timestamp in audio_files:
            
            timestamps.append(timestamp)
            




# print("Video files:\n", video_files)
# print("\nAudio files: \n", audio_files)

# avpairs = []

# # Join matching video and audio files
# for video_file in video_files: 
    # pair = []
    # for audio_file in audio_files:
        # video_timestamp = video_file.split('-')[1:]
        # #remove .avi
        # video_timestamp[-1] = video_timestamp[-1][:2]
        # audio_timestamp = audio_file.split('-')[1:]
        # #remove .wav
        # audio_timestamp[-1] = audio_timestamp[-1][:2]
        # if ("".join(audio_timestamp) == "".join(video_timestamp)):
            # avpairs.append([audio_file, video_file])
            # break

# for pair in avpairs:
    # for entry in logArr:
        # print("ENTRY: ",entry)
        # if entry[0] == pair[1]:
            # pair.append(entry[1:])
# print("\nAV Pairs:\n",avpairs)

for timestamp in timestamps:

    try:
        audio_filename = "./DASH0-Audio/"+timestamp+".wav"
        audioDuration = getLength(audio_filename)
        
        video_filename = "./DASH0-Video/"+timestamp+".avi"
        videoDuration = getLength(video_filename)
        
        merged_filename = "./AV/"+timestamp+".avi"
        
        cmd = "ffmpeg -i " + video_filename + " -i " + audio_filename + """ -filter_complex "[0:v]setpts=PTS*""" + str(audioDuration) + "/" + str(videoDuration) + """[v]" -map "[v]" -map 1:a -shortest """ + merged_filename
        
        subprocess.call(cmd, shell=True)
        
        # if abs(data["fps"] - 6) >= 0.01:
            # print("FPS: ",data["fps"])
            # print("Duration: ",data["duration"]
            # print("Audio Duration: ",data["audioDuration"])
            # cmd = "ffmpeg -r " + \
                # str(data["fps"]) + \
                # " -i "+video_filename+" -pix_fmt yuv420p -r 6 temp_video2.avi"
            # subprocess.call(cmd, shell=True)

            # cmd = "ffmpeg -ac 2 -channel_layout stereo -i "+audio_filename+" -i temp_video2.avi -pix_fmt yuv420p " + merged_filename
            # subprocess.call(cmd, shell=True)
            # os.remove(str(mypath) + "/temp_video2.avi")

        # else:
            # cmd = "ffmpeg -ac 2 -channel_layout stereo -i "+audio_filename+" -i "+video_filename+" -pix_fmt yuv420p " + merged_filename
            # subprocess.call(cmd, shell=True)
        # # os.remove(str(mypath) + "/"+audio_filename)
        # # os.remove(str(mypath) + "/"+video_filename)
        # print("Replaced "+audio_filename+" and "+video_filename+" with: \nNEW FILE: "+merged_filename)
        # # Erase merge log
        # # with open("avmergelog.txt", "w") as f:
        # #     f.write("")
    except Exception as e:
        print("Skipping because error:",e)
    

