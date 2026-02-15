import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import subprocess
import os

MODEL = whisper.load_model("base")
SAMPLE_RATE = 44100 #16000

def record_manual(filename="input.wav"):
    input("Press ENTER to start recording...")
    print("🎤 Recording... Press ENTER to stop.")

    recording = []
    is_recording = True

    def callback(indata, frames, time, status):
        if is_recording:
            recording.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=callback
    )

    with stream:
        input()
        is_recording = False

    audio = np.concatenate(recording, axis=0)
    write(filename, SAMPLE_RATE, audio)
    print("Recording saved.")

def listen():
    choice = input("Do you want to (1) write or (2) speak? ")

    if choice == "1":
        return input("Write your message: ")

    elif choice == "2":
        record_manual()
        result = MODEL.transcribe("input.wav")
        transcript = result["text"]

        # Save transcript to file
        filename = "transcript.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(transcript)

        print("\nOpening transcript in Notepad for editing...")
        
        # Open Notepad and wait until it closes
        subprocess.run(["notepad.exe", filename])

        # Read corrected version
        with open(filename, "r", encoding="utf-8") as f:
            corrected_text = f.read().strip()

        os.remove(filename)
        return corrected_text

    else:
        print("Invalid choice.")
        return ""