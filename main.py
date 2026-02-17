import requests
import json
import random
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import os
import time
from tts import speak
from stt import listen

# Ollama Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_MODEL = "llama2"
DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 500

# DM System Prompt
DM_SYSTEM_PROMPT = """You are an experienced Dungeon Master running a Dungeons & Dragons 5th Edition game.

CRITICAL RULES:
- You are the DM. You describe the world, NPCs, monsters, and consequences.
- NEVER control player characters. NEVER decide what players say or do.
- NEVER railroad the story. Let players make their own choices.
- Always ask players what they want to do next.
- Request dice rolls when actions require skill checks, attacks, or saves (e.g., "Roll a d20 + your Dexterity modifier for Stealth").
- During combat, track initiative order and ask each player for their action on their turn.
- Use vivid but concise descriptions (2-4 sentences typically).
- Stay in character as a DM at all times.
- When players take damage or are healed, state the HP change clearly.
- Create engaging encounters, NPCs, and plot hooks.
- Be fair but challenging.

Current game state will be provided with each prompt. Use it to maintain continuity."""


class MessageType(Enum):
    DM = "DM"
    PLAYER = "PLAYER"
    SYSTEM = "SYSTEM"


@dataclass
class Player:
    name: str
    char_class: str
    hp: int
    max_hp: int
    status: str = "Active"
    
    def to_dict(self):
        return asdict(self)
    
    def __str__(self):
        return f"{self.name} ({self.char_class}): {self.hp}/{self.max_hp} HP - {self.status}"


@dataclass
class Message:
    sender: str
    content: str
    msg_type: MessageType


@dataclass
class GameState:
    players: List[Player]
    current_player_index: int
    location: str
    in_combat: bool
    story_summary: str
    messages: List[Message]
    
    def to_context_string(self) -> str:
        """Convert game state to string for LLM context"""
        context = f"GAME STATE:\n"
        context += f"Location: {self.location}\n"
        context += f"Combat Active: {self.in_combat}\n"
        context += f"Story Summary: {self.story_summary}\n\n"
        context += f"PLAYERS:\n"
        for i, player in enumerate(self.players):
            active = " [CURRENT TURN]" if i == self.current_player_index else ""
            context += f"- {player.name} ({player.char_class}): {player.hp}/{player.max_hp} HP - {player.status}{active}\n"
        return context


class DiceRoller:
    @staticmethod
    def roll(dice_type: int, modifier: int = 0) -> tuple:
        result = random.randint(1, dice_type)
        total = result + modifier
        return result, total
    
    @staticmethod
    def parse_and_roll(dice_string: str) -> str:
        try:
            dice_string = dice_string.lower().strip()
            modifier = 0
            
            if '+' in dice_string:
                parts = dice_string.split('+')
                dice_string = parts[0]
                modifier = int(parts[1])
            elif '-' in dice_string:
                parts = dice_string.split('-')
                dice_string = parts[0]
                modifier = -int(parts[1])
            
            if 'd' in dice_string:
                parts = dice_string.split('d')
                num_dice = int(parts[0]) if parts[0] else 1
                dice_type = int(parts[1])
                
                rolls = [random.randint(1, dice_type) for _ in range(num_dice)]
                total = sum(rolls) + modifier
                
                result = f"Rolled {num_dice}d{dice_type}"
                if modifier != 0:
                    result += f"{'+' if modifier > 0 else ''}{modifier}"
                result += f": [{', '.join(map(str, rolls))}]"
                if modifier != 0:
                    result += f" {'+' if modifier > 0 else ''}{modifier}"
                result += f" = {total}"
                return result
            else:
                return "Invalid dice format"
        except:
            return "Invalid dice format"


class OllamaClient:

    def __init__(self, model: str, temperature: float, max_tokens: int):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.connected = False
        self.available_models = []
    
    def check_connection(self) -> bool:
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [model['name'] for model in data.get('models', [])]
                self.connected = True
                return True
            else:
                self.connected = False
                return False
        except requests.exceptions.ConnectionError:
            self.connected = False
            return False
        except requests.exceptions.Timeout:
            self.connected = False
            return False
        except Exception as e:
            print(f"Unexpected error checking Ollama: {e}")
            self.connected = False
            return False
    
    def verify_model(self, model_name: str) -> bool:
        if not self.connected:
            if not self.check_connection():
                return False
        
        return model_name in self.available_models
    
    def list_available_models(self) -> List[str]:
        if not self.connected:
            self.check_connection()
        return self.available_models
    
    def generate(self, prompt: str, system_prompt: str) -> Optional[str]:
        if not self.connected:
            if not self.check_connection():
                return None
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json().get("response", "")
            elif response.status_code == 404:
                print(f"\nError: Model '{self.model}' not found!")
                print(f"Available models: {', '.join(self.available_models)}")
                return None
            else:
                print(f"\nOllama returned status code: {response.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            print("\nError: Lost connection to Ollama!")
            self.connected = False
            return None
        except requests.exceptions.Timeout:
            print("\nError: Ollama request timed out!")
            return None
        except Exception as e:
            print(f"\nOllama error: {e}")
            return None


class DnDGame:
    def __init__(self):
        self.game_state = None
        self.ollama = OllamaClient(DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS)
        self.running = True
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_separator(self, char="=", length=80):
        print(char * length)
    
    def print_header(self, text):
        self.print_separator()
        print(f"  {text}")
        self.print_separator()
    
    def verify_ollama_connection(self) -> bool:
        self.clear_screen()
        self.print_header("CHECKING OLLAMA CONNECTION")
        
        print("\nChecking if Ollama is running...", end=" ", flush=True)
        
        if not self.ollama.check_connection():
            print("✗ FAILED")
            print("\n" + "!" * 80)
            print("ERROR: Cannot connect to Ollama!")
            print("!" * 80)
            print("\nPlease make sure:")
            print("  1. Ollama is installed")
            print("  2. Ollama service is running")
            print("  3. Ollama is accessible at http://localhost:11434")
            print("\nTo start Ollama, run: ollama serve")
            print("\nPress Enter to retry, or 'q' to quit...")
            
            choice = input().strip().lower()
            if choice == 'q':
                return False
            else:
                return self.verify_ollama_connection()
        
        print("✓ CONNECTED")
        
        print(f"\nAvailable models: {', '.join(self.ollama.available_models)}")
        
        if not self.ollama.verify_model(self.ollama.model):
            print(f"\n⚠ Warning: Model '{self.ollama.model}' not found!")
            
            if len(self.ollama.available_models) == 0:
                print("\nNo models installed!")
                print("Please install a model first. Example:")
                print("  ollama pull llama2")
                print("  ollama pull mistral")
                print("\nPress Enter to exit...")
                input()
                return False
            
            print("\nAvailable models:")
            for i, model in enumerate(self.ollama.available_models, 1):
                print(f"  {i}. {model}")
            
            print(f"\nSelect a model (1-{len(self.ollama.available_models)}), or press Enter to use '{self.ollama.available_models[0]}':")
            choice = input().strip()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(self.ollama.available_models):
                    self.ollama.model = self.ollama.available_models[idx]
                else:
                    self.ollama.model = self.ollama.available_models[0]
            else:
                self.ollama.model = self.ollama.available_models[0]
            
            print(f"\n✓ Using model: {self.ollama.model}")
        else:
            print(f"\n✓ Model '{self.ollama.model}' is available")
        
        print("\nTesting model response...", end=" ", flush=True)
        test_response = self.ollama.generate("Say 'ready' if you can hear me.", "You are a helpful assistant.")
        
        if test_response:
            print("✓ SUCCESS")
            print(f"\nModel response: {test_response[:100]}...")
        else:
            print("✗ FAILED")
            print("\nCould not get a response from the model.")
            print("Press Enter to retry, or 'q' to quit...")
            choice = input().strip().lower()
            if choice == 'q':
                return False
            else:
                return self.verify_ollama_connection()
        
        print("\n✓ Ollama is ready!")
        input("\nPress Enter to continue...")
        return True
    
    def setup_players(self) -> List[Player]:
        """Setup phase - create players"""
        self.clear_screen()
        self.print_header("D&D DUNGEON MASTER - CHARACTER SETUP")
        
        players = []
        
        print("\nCreate your adventuring party!")
        print("Enter player details (leave name empty to finish)\n")
        
        while True:
            print(f"\n--- Player {len(players) + 1} ---")
            name = input("Character Name (or press Enter to finish): ").strip()
            
            if not name:
                if len(players) == 0:
                    print("You need at least one player!")
                    continue
                break
            
            char_class = input("Class (e.g., Fighter, Wizard, Rogue): ").strip()
            if not char_class:
                char_class = "Adventurer"
            
            while True:
                try:
                    hp = int(input("Max HP: ").strip())
                    if hp > 0:
                        break
                    print("HP must be positive!")
                except ValueError:
                    print("Please enter a valid number!")
            
            player = Player(name=name, char_class=char_class, hp=hp, max_hp=hp)
            players.append(player)
            print(f"✓ Added {player}")
        
        print(f"\n✓ Party created with {len(players)} player(s)!")
        input("\nPress Enter to begin the adventure...")
        
        return players
    
    def init_game_state(self, players: List[Player]):
        """Initialize the game state"""
        self.game_state = GameState(
            players=players,
            current_player_index=0,
            location="Unknown",
            in_combat=False,
            story_summary="The adventure begins...",
            messages=[]
        )
    
    def send_to_dm(self, player_message: str) -> Optional[str]:
        """Send a message to the DM and get response"""
        print("\n[DM is thinking...]", end= "\r\r\r")
        
        full_prompt = self.game_state.to_context_string() + "\n\n"
        
        recent_messages = self.game_state.messages[-10:]
        if recent_messages:
            full_prompt += "RECENT CONVERSATION:\n"
            for msg in recent_messages:
                if msg.msg_type == MessageType.DM:
                    full_prompt += f"DM: {msg.content}\n"
                elif msg.msg_type == MessageType.PLAYER:
                    full_prompt += f"{msg.sender}: {msg.content}\n"
            full_prompt += "\n"
        
        full_prompt += f"CURRENT INPUT:\n{player_message}\n\nDM RESPONSE:"
        
        # Call Ollama
        response = self.ollama.generate(full_prompt, DM_SYSTEM_PROMPT)
        
        if response:
            dm_message = Message("DM", response.strip(), MessageType.DM)
            self.game_state.messages.append(dm_message)

            return response.strip()
        else:
            return None
    
    def display_game_state(self):
        self.clear_screen()
        self.print_header("D&D DUNGEON MASTER")
        
        print("\n--- PARTY STATUS ---")
        for i, player in enumerate(self.game_state.players):
            marker = "→" if i == self.game_state.current_player_index else " "
            print(f"{marker} {player}")
        
        print(f"\nLocation: {self.game_state.location}")
        print(f"Combat: {'YES' if self.game_state.in_combat else 'NO'}")
        
        # Show connection status
        status_icon = "✓" if self.ollama.connected else "✗"
        print(f"Ollama: {status_icon} {self.ollama.model}")
        
        self.print_separator("-")
    
    def show_commands(self):
        print("\nCOMMANDS:")
        print("  /roll [dice]  - Roll dice (e.g., /roll d20, /roll 2d6+3)")
        print("  /next         - Switch to next player")
        print("  /prev         - Switch to previous player")
        print("  /status       - Show party status")
        print("  /hp [name] [amount] - Adjust HP (e.g., /hp Gandalf -5)")
        print("  /settings     - Change Ollama settings")
        print("  /reconnect    - Reconnect to Ollama")
        print("  /quit         - Exit game")
        print("  /help         - Show this help")
        print()
    
    def handle_command(self, command: str) -> bool:
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/quit":
            print("\nThanks for playing!")
            self.running = False
            return True
        
        elif cmd == "/help":
            self.show_commands()
            return True
        
        elif cmd == "/status":
            self.display_game_state()
            return True
        
        elif cmd == "/reconnect":
            print("\nReconnecting to Ollama...")
            if self.ollama.check_connection():
                print(f"✓ Reconnected! Available models: {', '.join(self.ollama.available_models)}")
            else:
                print("✗ Failed to reconnect. Make sure Ollama is running.")
            return True
        
        elif cmd == "/next":
            self.game_state.current_player_index = (self.game_state.current_player_index + 1) % len(self.game_state.players)
            current = self.game_state.players[self.game_state.current_player_index]
            print(f"\n→ Switched to {current.name}")
            return True
        
        elif cmd == "/prev":
            self.game_state.current_player_index = (self.game_state.current_player_index - 1) % len(self.game_state.players)
            current = self.game_state.players[self.game_state.current_player_index]
            print(f"\n→ Switched to {current.name}")
            return True
        
        elif cmd == "/roll":
            if len(parts) < 2:
                print("\nUsage: /roll [dice] (e.g., /roll d20, /roll 2d6+3)")
                return True
            
            dice_str = parts[1]
            result = DiceRoller.parse_and_roll(dice_str)
            current_player = self.game_state.players[self.game_state.current_player_index]
            print(f"\n[{current_player.name}] {result}")
            
            msg = Message(current_player.name, f"Rolled {result}", MessageType.PLAYER)
            self.game_state.messages.append(msg)
            return True
        
        elif cmd == "/hp":
            if len(parts) < 3:
                print("\nUsage: /hp [player_name] [amount]")
                print("Example: /hp Gandalf -5  (take 5 damage)")
                print("Example: /hp Gandalf +10 (heal 10 HP)")
                return True
            
            player_name = parts[1]
            try:
                amount = int(parts[2])
            except ValueError:
                print("\nInvalid amount!")
                return True
            
            player = None
            for p in self.game_state.players:
                if p.name.lower() == player_name.lower():
                    player = p
                    break
            
            if not player:
                print(f"\nPlayer '{player_name}' not found!")
                return True
            
            player.hp += amount
            player.hp = max(0, min(player.hp, player.max_hp))
            
            if amount > 0:
                print(f"\n{player.name} healed {amount} HP → {player.hp}/{player.max_hp} HP")
            else:
                print(f"\n{player.name} took {abs(amount)} damage → {player.hp}/{player.max_hp} HP")
            
            if player.hp == 0:
                player.status = "Unconscious"
                print(f"⚠ {player.name} has fallen unconscious!")
            elif player.status == "Unconscious" and player.hp > 0:
                player.status = "Active"
                print(f"✓ {player.name} is back on their feet!")
            
            return True
        
        elif cmd == "/settings":
            print("\n--- OLLAMA SETTINGS ---")
            print(f"Current Model: {self.ollama.model}")
            print(f"Temperature: {self.ollama.temperature}")
            print(f"Max Tokens: {self.ollama.max_tokens}")
            print(f"\nAvailable models: {', '.join(self.ollama.available_models)}")
            
            new_model = input("\nNew model (or Enter to keep current): ").strip()
            if new_model:
                if self.ollama.verify_model(new_model):
                    self.ollama.model = new_model
                    print(f"✓ Model changed to {new_model}")
                else:
                    print(f"✗ Model '{new_model}' not found!")
            
            new_temp = input("New temperature (or Enter to keep current): ").strip()
            if new_temp:
                try:
                    self.ollama.temperature = float(new_temp)
                    print(f"✓ Temperature set to {self.ollama.temperature}")
                except ValueError:
                    print("✗ Invalid temperature!")
            
            new_tokens = input("New max tokens (or Enter to keep current): ").strip()
            if new_tokens:
                try:
                    self.ollama.max_tokens = int(new_tokens)
                    print(f"✓ Max tokens set to {self.ollama.max_tokens}")
                except ValueError:
                    print("✗ Invalid token count!")
            
            print("\n✓ Settings updated!")
            return True
        
        return False
    
    def game_loop(self):
        self.display_game_state()
        
        print("\n[SYSTEM] Game started! The DM is preparing your adventure...")
        response = self.send_to_dm("The players have gathered. Begin the adventure by describing the starting scene and asking what they would like to do.")
        
        if response:
            print(f"[DM] {response}\n")
            time.sleep(0.3)
            speak(response)
            time.sleep(0.5)
            os.remove("story.mp3")
        else:
            print("[ERROR] Could not get initial response from DM.")
            print("Check your Ollama connection with /reconnect")
        
        self.show_commands()
        
        while self.running:
            current_player = self.game_state.players[self.game_state.current_player_index]
            
            choice = input(f"\n[{current_player.name}] Do you want to (1) write or (2) speak? ")

            if choice == "1":
                user_input = input(f"[{current_player.name}] > ").strip()
            elif choice == "2":
                user_input = listen()
            else:
                print("Invalid choice, defaulting to write.")
                user_input = input(f"[{current_player.name}] > ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith('/'):
                if self.handle_command(user_input):
                    continue
            
            player_msg = Message(current_player.name, user_input, MessageType.PLAYER)
            self.game_state.messages.append(player_msg)
            
            response = self.send_to_dm(f"{current_player.name} says/does: {user_input}")
            
            if response:
                print(f"[DM] {response}")
            else:
                print("[ERROR] Could not reach Ollama. Use /reconnect to retry connection.")
    
    def run(self):
        try:
            if not self.verify_ollama_connection():
                print("\nCannot start without Ollama connection. Exiting...")
                return
            
            players = self.setup_players()
            self.init_game_state(players)

            self.game_loop()
            
        except KeyboardInterrupt:
            print("\n\nGame interrupted. Thanks for playing!")
        except Exception as e:
            print(f"\n\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    game = DnDGame()
    game.run()