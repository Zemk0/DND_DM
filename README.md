# 🐉 DragonMaster – D&D 5e Roleplay Assistant

DragonMaster is a Python-based **Dungeon Master assistant** for running **Dungeons & Dragons 5th Edition** games. It combines **AI-generated storytelling**, **manual speech-to-text input**, and **cinematic text-to-speech output** to create a fully immersive tabletop RPG experience.

Players can either **type their actions** or **speak them manually**, and the DM responds both in text and voice, keeping the adventure dynamic and engaging.

---

## ⚡ Features

* AI-powered Dungeon Master using **Ollama LLM models**
* Manual **speech-to-text** for player actions
* **Cinematic TTS** narration for DM messages
* Dice rolling system (`d20`, `2d6+3`, etc.)
* Party and HP tracking
* Combat management and initiative tracking
* Fully modular and extendable

---

## 🛠 Installation

### 1. Install Python 3.10+

Make sure Python 3.10 or higher is installed.

### 2. Install Ollama

DragonMaster requires a local **Ollama server** to generate DM responses.

1. Install Ollama: [https://ollama.com](https://ollama.com)
2. Pull a model, e.g., `llama2`:

```bash
ollama pull llama2
```

3. Start the Ollama server:

```bash
ollama serve
```

The default server URL is `http://localhost:11434`.

---

### 3. Install Python Dependencies

All required Python packages are listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

This installs:

* `edge-tts` / `pyttsx3` → DM voice narration
* `openai-whisper` + `sounddevice` → player speech recognition
* `requests` → Ollama API communication
* `pygame` → smooth audio playback
* `keyboard` → manual key control

---

## 🚀 Usage

1. Run the main script:

```bash
python DM.py
```

2. Follow prompts to:

* Verify Ollama connection
* Set up player characters
* Start your adventure

3. During gameplay:

* Type `/help` for a list of commands
* Choose to **write or speak** each turn
* DM messages are narrated automatically

---

## 🎲 Supported Commands

* `/roll [dice]` → Roll dice (e.g., `/roll d20`, `/roll 2d6+3`)
* `/next` / `/prev` → Switch to next/previous player
* `/hp [name] [amount]` → Adjust player HP
* `/status` → Show party status
* `/settings` → Change Ollama settings
* `/reconnect` → Reconnect to Ollama
* `/quit` → Exit game

---

## 📜 Notes

* Works on **Windows, macOS, and Linux**
* Requires **microphone** for STT and **speakers/headphones** for TTS
* Designed for **DnD 5e campaigns**, but can be adapted for other RPG systems
