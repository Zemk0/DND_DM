import asyncio
import edge_tts
import pygame
import time

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
    asyncio.run(generate_voice(text))

    pygame.mixer.music.load("story.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
