import asyncio
import edge_tts
import pygame
import time
import os

VOICE = "en-GB-RyanNeural"

pygame.mixer.init()

async def generate_voice(text, filename="story.mp3"):
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate="-7%",
        pitch="-15Hz"
    )
    await communicate.save(filename)

def speak(text):
    if os.path.exists("story.mp3"):
        os.remove("story.mp3")
    asyncio.run(generate_voice(text))

    pygame.mixer.music.load("story.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
