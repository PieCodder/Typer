
import time
import json
import numpy as np
import queue

# Helper function for profile calculation (pure logic)
def calculate_profile(delays, backspace_count, total_chars):
    if not delays:
        return None
        
    delays_np = np.array(delays)
    mean_delay = np.mean(delays_np)
    std_dev = np.std(delays_np)
    
    # Estimated WPM
    estimated_wpm = int((60.0 / mean_delay) / 5) if mean_delay > 0 else 0
    
    # Mistake Rate
    mistake_rate = 0.0
    if total_chars > 0:
        mistake_rate = backspace_count / total_chars
        
    # We save a sample of delays (normalized) to mimic the "texture" of typing
    # Normalize by mean to get factors (e.g. 0.5 = fast char, 2.0 = pause)
    normalized_delays = (delays_np / mean_delay).tolist() if mean_delay > 0 else []
    
    # Limit sample size to avoid huge files
    if len(normalized_delays) > 1000:
        normalized_delays = list(np.random.choice(normalized_delays, 1000))
    
    return {
        'mean_delay': float(mean_delay),
        'std_dev': float(std_dev),
        'sample_size': len(delays),
        'wpm': estimated_wpm,
        'mistake_rate': float(mistake_rate),
        'delay_samples': normalized_delays
    }

def merge_profiles(old_profile, new_profile):
    """
    Merges a new recording session into an existing profile.
    Uses weighted averages based on sample_size.
    """
    if not old_profile:
        return new_profile
    if not new_profile:
        return old_profile
        
    n1 = old_profile.get('sample_size', 0)
    n2 = new_profile.get('sample_size', 0)
    
    if n2 == 0: return old_profile
    if n1 == 0: return new_profile
    
    total_samples = n1 + n2
    
    # Weighted Averages
    new_mean = (old_profile['mean_delay'] * n1 + new_profile['mean_delay'] * n2) / total_samples
    new_wpm = int((old_profile['wpm'] * n1 + new_profile['wpm'] * n2) / total_samples)
    new_mistake_rate = (old_profile['mistake_rate'] * n1 + new_profile['mistake_rate'] * n2) / total_samples
    
    # Std Dev pooling (approximation)
    # Combined variance = (n1*(var1 + d1^2) + n2*(var2 + d2^2)) / (n1+n2)
    # where d1 = m1 - m_new, d2 = m2 - m_new
    var1 = old_profile['std_dev'] ** 2
    var2 = new_profile['std_dev'] ** 2
    d1 = old_profile['mean_delay'] - new_mean
    d2 = new_profile['mean_delay'] - new_mean
    
    combined_variance = (n1 * (var1 + d1**2) + n2 * (var2 + d2**2)) / total_samples
    new_std_dev = float(np.sqrt(combined_variance))
    
    # Merge delay samples (Texture)
    # We want to keep growing the pool but cap it so it doesn't get huge.
    # New samples should be re-normalized effectively? 
    # Actually, delay_samples in profile are factors (delay / mean). 
    # Since the mean is changing slightly, strictly speaking we should re-normalize, 
    # but since it's just texture noise, appending is 'okay' enough for this use case.
    # A better approach might be to just keep them as raw factors.
    
    merged_delays = old_profile.get('delay_samples', []) + new_profile.get('delay_samples', [])
    
    # Simple cap: Keep most recent 5000 samples? Or random subset? 
    # To represent "better" learning, we should keep a good mix.
    if len(merged_delays) > 5000:
        merged_delays = list(np.random.choice(merged_delays, 5000))

    return {
        'mean_delay': float(new_mean),
        'std_dev': new_std_dev,
        'sample_size': total_samples,
        'wpm': new_wpm,
        'mistake_rate': float(new_mistake_rate),
        'delay_samples': merged_delays
    }

def run_recorder_process(command_queue, result_queue):
    """
    Worker process for recording keystrokes.
    cmds:
    - "START": Begin recording
    - "STOP": Stop recording and send back profile via result_queue
    - "KILL": Terminate
    """
    print("RECORDER: Starting Worker Process...")
    
    # Import pynput ONLY here to avoid main process conflicts on macOS
    try:
        from pynput import keyboard
    except ImportError:
        print("RECORDER: pynput not found!")
        return

    delays = []
    last_time = None
    is_recording = False
    
    # New stats
    backspace_count = 0
    total_chars = 0
    
    def on_press(key):
        nonlocal last_time, backspace_count, total_chars
        if not is_recording:
            return

        current_time = time.time()
        
        # Track counts
        if key == keyboard.Key.backspace:
            backspace_count += 1
        elif hasattr(key, 'char'):
             total_chars += 1
        
        if last_time is not None:
            delay = current_time - last_time
            # Filter out extremely long pauses (e.g. > 2 seconds)
            if delay < 2.0:
                delays.append(delay)
        
        last_time = current_time

    def on_release(key):
        pass

    # Start listener
    try:
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        print("RECORDER: Listener started.")
    except Exception as e:
        print(f"RECORDER: Failed to start listener: {e}")
        return

    while True:
        try:
            # Blocking get is fine because listener is in a separate thread (pynput default)
            cmd = command_queue.get()
            
            if cmd == "KILL":
                print("RECORDER: Received KILL.")
                listener.stop()
                return
            
            elif cmd == "START":
                print("RECORDER: Starting recording...")
                delays = []
                last_time = None
                is_recording = True
                backspace_count = 0
                total_chars = 0
                
            elif cmd == "STOP":
                print("RECORDER: Stopping recording...")
                is_recording = False
                profile = calculate_profile(delays, backspace_count, total_chars)
                # Send result back to GUI
                if profile:
                    result_queue.put(profile)
                else:
                    # Send empty profile to indicate no data
                    result_queue.put({'sample_size': 0, 'wpm': 0})
                    
        except Exception as e:
            print(f"RECORDER: Error in loop: {e}")
