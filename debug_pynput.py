
import sys
print("Debug: Script started")

try:
    print("Debug: Importing pynput...")
    from pynput import keyboard
    print("Debug: pynput imported successfully")
except Exception as e:
    print(f"Debug: Failed to import pynput: {e}")
    sys.exit(1)

def on_press(key):
    print(f"Debug: Key pressed: {key}")
    return False # Stop listener immediately

print("Debug: Creating listener...")
try:
    listener = keyboard.Listener(on_press=on_press)
    print("Debug: Listener created. Starting...")
    listener.start()
    print("Debug: Listener started. Waiting for join...")
    listener.join()
    print("Debug: Listener finished.")
except Exception as e:
    print(f"Debug: Error with listener: {e}")

print("Debug: Script finished")
