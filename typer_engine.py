
import time
import random
import threading
import multiprocessing
import queue
import numpy as np

# Pynput must be imported safely. 
# We will import it inside the process function or at top level, 
# but the listener must strictly belong to the child process.
from pynput.keyboard import Controller, Key, Listener

class TyperEngine:
    def __init__(self):
        self.keyboard = Controller()
        self.stop_event = threading.Event()

    def type_text(self, text, wpm=60, profile=None):
        if not text:
            return
        
        self.stop_event.clear() # Ensure event is clear at start of typing
        
        # Calculate base delay
        base_delay = 60.0 / (wpm * 5) if wpm > 0 else 0.1
        
        # Mistake Chance
        mistake_chance = max(0.01, (wpm / 150.0) * 0.10) # Default logic
        if profile and 'mistake_rate' in profile:
             # Scale user mistake rate by Speed multiplier?
             # For now, let's use the recorded rate directly but allow it to scale if they type faster than their recording.
             # Actually, simpler: Use recorded rate if speed matches, else scale.
             # Let's just use the recorded rate as a baseline.
             mistake_chance = profile['mistake_rate']
             # If WPM is much higher than profile WPM, increase chance slightly?
             if profile.get('wpm', 0) > 0 and wpm > profile['wpm']:
                 ratio = wpm / profile['wpm']
                 mistake_chance *= ratio

        try:
            for char in text:
                if self.stop_event.is_set():
                    break
                
                # Check for mistake
                if random.random() < mistake_chance and char.lower() in self.QWERTY_MAP:
                    typo_char = random.choice(self.QWERTY_MAP[char.lower()])
                    if char.isupper():
                        typo_char = typo_char.upper()
                    
                    # Type wrong key
                    self.keyboard.type(typo_char)
                    time.sleep(self._calculate_delay(base_delay, profile) * 0.8) 
                    
                    # Backspace
                    self.keyboard.press(Key.backspace)
                    self.keyboard.release(Key.backspace)
                    time.sleep(self._calculate_delay(base_delay, profile) * 0.5)
                
                # Determine delay for correct char
                delay = self._calculate_delay(base_delay, profile)
                
                # Type the character
                self.keyboard.type(char)
                
                # Sleep
                time.sleep(delay)
                
                if self.stop_event.is_set(): # Check again after sleep
                    break

        except Exception as e:
            print(f"Error during typing: {e}")

    QWERTY_MAP = {
        'q': ['w', 'a', '1'], 'w': ['q', 'e', 's', '2'], 'e': ['w', 'r', 'd', '3'], 'r': ['e', 't', 'f', '4'], 't': ['r', 'y', 'g', '5'], 'y': ['t', 'u', 'h', '6'], 'u': ['y', 'i', 'j', '7'], 'i': ['u', 'o', 'k', '8'], 'o': ['i', 'p', 'l', '9'], 'p': ['o', 'l', '0'],
        'a': ['q', 's', 'z'], 's': ['a', 'w', 'd', 'x', 'z'], 'd': ['s', 'e', 'f', 'c', 'x'], 'f': ['d', 'r', 'g', 'v', 'c'], 'g': ['f', 't', 'h', 'b', 'v'], 'h': ['g', 'y', 'j', 'n', 'b'], 'j': ['h', 'u', 'k', 'm', 'n'], 'k': ['j', 'i', 'l', 'm'], 'l': ['k', 'o', 'p'],
        'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'], 'c': ['x', 'd', 'f', 'v'], 'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'], 'n': ['b', 'h', 'j', 'm'], 'm': ['n', 'j', 'k']
    }

    def _calculate_delay(self, base_delay, profile):
        # Rich Profile: Use sampled distribution if available
        if profile and 'delay_samples' in profile and profile['delay_samples']:
            # Pick a random normalized sample
            factor = random.choice(profile['delay_samples'])
            # Apply to base_delay (which is based on current Target WPM)
            return max(0.01, base_delay * factor)
            
        elif profile and 'mean_delay' in profile:
            mean = profile.get('mean_delay', base_delay)
            std = profile.get('std_dev', base_delay * 0.2)
            delay = np.random.normal(mean, std)
        else:
            std = base_delay * 0.25
            delay = np.random.normal(base_delay, std)
        return max(0.01, delay)

def run_typer_process(command_queue):
    """
    Worker process that handles keyboard listening and typing.
    Communicates via command_queue:
    - ("ENABLE", None)
    - ("DISABLE", None)
    - ("UPDATE_TEXT", text_string)
    - ("UPDATE_SPEED", wpm_int)
    - ("UPDATE_PROFILE", profile_dict)
    - ("KILL", None)
    """
    print("WORKER: Starting Typer Worker Process...")
    
    engine = TyperEngine()
    
    # State
    enabled = False
    current_text = ""
    current_wpm = 60
    current_profile = None
    
    # We need a way to check the queue AND listen for keys.
    # Pynput listener is blocking if we use .join(), but non-blocking if we just .start().
    # We will use a non-blocking listener strategy or a check loop.
    
    trigger_key_pressed = False
    
    def on_release(key):
        nonlocal trigger_key_pressed
        # We only care if enabled
        if not enabled:
            return

        if key == Key.shift_r:
            # We set a flag, and the main loop handles the typing.
            # This avoids running heavy typing logic inside the callback thread.
            trigger_key_pressed = True

    # Start the listener in this process
    try:
        listener = Listener(on_release=on_release)
        listener.start()
        print("WORKER: Listener started.")
    except Exception as e:
        print(f"WORKER: Failed to start listener: {e}")
        return

    typing_thread = None

    while True:
        # 1. Check for commands from GUI
        try:
            while True: 
                cmd, data = command_queue.get_nowait()
                if cmd == "KILL":
                    print("WORKER: Received KILL. Exiting.")
                    if typing_thread and typing_thread.is_alive():
                        engine.stop_typing()
                    listener.stop()
                    return
                elif cmd == "ENABLE":
                    enabled = True
                    print("WORKER: Enabled.")
                elif cmd == "DISABLE":
                    enabled = False
                    engine.stop_typing() # Stop current typing if any
                    print("WORKER: Disabled.")
                elif cmd == "UPDATE_TEXT":
                    current_text = data
                    print(f"WORKER: Text updated (len={len(data)}).")
                elif cmd == "UPDATE_SPEED":
                    current_wpm = int(data)
                elif cmd == "UPDATE_PROFILE":
                    current_profile = data
                    print("WORKER: Profile updated.")
        except queue.Empty:
            pass

        # 2. Check if triggered
        if trigger_key_pressed:
            print("WORKER: Triggered! Typing...")
            # Reset flag immediately so we don't loop forever
            trigger_key_pressed = False
            
            # Check if already typing
            if typing_thread and typing_thread.is_alive():
                print("WORKER: Already typing, ignoring new trigger.")
            else:
                # Start new typing thread
                # engine.stop_event.clear() -> handled in type_text now
                typing_thread = threading.Thread(target=engine.type_text, args=(current_text, current_wpm, current_profile))
                typing_thread.start()

        # Sleep a tiny bit to prevent CPU hogs
        time.sleep(0.05)
