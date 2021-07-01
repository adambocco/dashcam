from pyaudio import PyAudio
import wave
import threading
import time

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
        self.format = 8
        self.audio_filename = filename+".wav"
        self.audio = PyAudio()
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
            time.sleep(0.5)
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            self.endTime = time.time()
            self.duration = self.endTime - self.startTime
            time.sleep(0.5)
            waveFile = wave.open(self.audio_filename, 'wb')
            waveFile.setnchannels(self.channels)
            waveFile.setsampwidth(self.audio.get_sample_size(self.format))
            waveFile.setframerate(self.rate)
            waveFile.writeframes(b''.join(self.audio_frames)) # Audio write out at this point
            waveFile.close()
        time.sleep(0.5)
        return self.duration

    # Launches the audio recording function using a thread
    def start(self):
        self.startTime = time.time()
        self.open = True
        self.audio_thread = threading.Thread(target=self.record)
        self.audio_thread.start()