
import customtkinter as ctk
import multiprocessing
import json
import os
import sys
import time
from typer_engine import run_typer_process
from recorder import run_recorder_process, merge_profiles

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TyperAPP(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Human-Like Typer")
        self.geometry("600x700")

        # Multiprocessing Setup
        self.queue = multiprocessing.Queue()
        self.worker_process = multiprocessing.Process(target=run_typer_process, args=(self.queue,), daemon=True)
        self.worker_process.start()

        # Recorder Process Setup
        self.recorder_queue_cmd = multiprocessing.Queue()
        self.recorder_queue_result = multiprocessing.Queue()
        self.recorder_process = multiprocessing.Process(target=run_recorder_process, args=(self.recorder_queue_cmd, self.recorder_queue_result), daemon=True)
        self.recorder_process.start()

        self.profile = None
        self.is_recording = False # GUI state
        self.is_enabled = False # Logical state
        
        self.profile_path = os.path.join(os.path.expanduser("~"), "typer_user_profile.json")
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # ... (Layout continues below, skipping unchanged parts for brevity if possible, but replace_file needs contiguous)
        # Re-declaring init layout to ensure clean replacement

        # Title
        self.label_title = ctk.CTkLabel(self, text="Human-Like Typer", font=("Roboto", 24))
        self.label_title.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Text Area
        self.textbox = ctk.CTkTextbox(self, width=500, height=300)
        self.textbox.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.textbox.insert("0.0", "Paste your text here...")

        # Controls Frame
        self.frame_controls = ctk.CTkFrame(self)
        self.frame_controls.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        self.frame_controls.grid_columnconfigure((0, 1), weight=1)

        # Speed Control
        self.label_speed = ctk.CTkLabel(self.frame_controls, text="Speed (WPM): 60")
        self.label_speed.grid(row=0, column=0, columnspan=2, pady=(10, 0))
        
        self.slider_speed = ctk.CTkSlider(self.frame_controls, from_=10, to=150, number_of_steps=140, command=self.update_speed_label)
        self.slider_speed.set(60)
        self.slider_speed.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        # Buttons
        self.btn_listen = ctk.CTkButton(self.frame_controls, text="Enable Typing (Right Shift)", command=self.toggle_enable)
        self.btn_listen.grid(row=2, column=0, padx=10, pady=10)

        self.btn_record = ctk.CTkButton(self.frame_controls, text="Record My Style", width=150, fg_color="#9C27B0", hover_color="#7B1FA2", command=self.toggle_recording)
        self.btn_record.grid(row=2, column=1, padx=5, pady=10)
        
        # Spacer for layout balance
        self.label_spacer = ctk.CTkLabel(self.frame_controls, text="")
        self.label_spacer.grid(row=2, column=2, padx=5, pady=10)

        # Profile Management Frame
        self.frame_profiles = ctk.CTkFrame(self)
        self.frame_profiles.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.frame_profiles.grid_columnconfigure(0, weight=1)
        
        # ... (rest of profile setup omitted from this chunk, assuming logic is sound)
        # Wait, need to close __init__ cleanly or replace_file might break.
        # Let's just define the new methods and `__init__` logic.
        
    def play_sound(self, sound_type="success"):
        # macOS specific sounds
        try:
            if sound_type == "success":
                os.system("afplay /System/Library/Sounds/Ping.aiff&")
            elif sound_type == "trigger":
                os.system("afplay /System/Library/Sounds/Pop.aiff&")
            elif sound_type == "error":
                os.system("afplay /System/Library/Sounds/Basso.aiff&")
        except:
            pass
            
    # ... (Rest of methods) ...

    def check_recorder_queue(self):
        try:
            while not self.recorder_queue_result.empty():
                profile = self.recorder_queue_result.get_nowait()
                self.process_recording_result(profile)
        except Exception as e:
            print(f"GUI: Queue Error: {e}")
        self.after(100, self.check_recorder_queue)
        
        self.label_profile = ctk.CTkLabel(self.frame_profiles, text="Select Profile:")
        self.label_profile.grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        
        self.combo_profiles = ctk.CTkComboBox(self.frame_profiles, values=["Default (Generic)"], command=self.on_profile_select)
        self.combo_profiles.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.combo_profiles.set("Default (Generic)")
        
        self.switch_match = ctk.CTkSwitch(self.frame_profiles, text="Use Profile Style (Auto-WPM)", command=self.toggle_match_mode)
        self.switch_match.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        # Status
        self.label_status = ctk.CTkLabel(self, text="Status: Idle", text_color="gray")
        self.label_status.grid(row=5, column=0, pady=10)
        
        # Profiles Directory
        self.profiles_dir = os.path.join(os.path.expanduser("~"), "HumanTyperProfiles")
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
            
        self.load_profiles_list()

        # Handle cleanup on close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Periodic check for recorder results
        self.check_recorder_queue()

        # Periodic check for recorder results
        self.check_recorder_queue()
        
        # Setup Global Hotkey Listener for Vision


    def load_profiles_list(self):
        import glob
        files = glob.glob(os.path.join(self.profiles_dir, "*.json"))
        names = [os.path.basename(f).replace(".json", "") for f in files]
        names.sort()
        self.profile_names = ["Default (Generic)"] + names
        self.combo_profiles.configure(values=self.profile_names)

    def on_profile_select(self, choice):
        if choice == "Default (Generic)":
            self.profile = None
            self.slider_speed.configure(state="normal")
            self.label_status.configure(text="Status: Selected Default Profile.", text_color="gray")
            # Update worker to clear profile
            self.queue.put(("UPDATE_PROFILE", None))
        else:
            path = os.path.join(self.profiles_dir, choice + ".json")
            try:
                with open(path, 'r') as f:
                    self.profile = json.load(f)
                self.label_status.configure(text=f"Status: Loaded '{choice}'.", text_color="#3B8ED0")
                
                # If match mode is ON, update speed immediately
                if self.switch_match.get() == 1:
                    self.apply_profile_speed()
                    
                # Send to worker
                self.queue.put(("UPDATE_PROFILE", self.profile))
            except Exception as e:
                print(f"Error loading profile: {e}")

    def toggle_match_mode(self):
        if self.switch_match.get() == 1:
            # Enable Match Mode
            if self.profile and 'wpm' in self.profile:
                self.apply_profile_speed()
                self.slider_speed.configure(state="disabled")
            else:
                if self.combo_profiles.get() == "Default (Generic)":
                     self.label_status.configure(text="Status: Create a profile first!", text_color="orange")
                     self.switch_match.deselect()
        else:
            # Disable Match Mode
            self.slider_speed.configure(state="normal")

    def apply_profile_speed(self):
        if self.profile and 'wpm' in self.profile:
            wpm = self.profile['wpm']
            self.slider_speed.set(wpm)
            self.update_speed_label(wpm)

    def check_recorder_queue(self):
        try:
            while not self.recorder_queue_result.empty():
                profile = self.recorder_queue_result.get_nowait()
                self.process_recording_result(profile)
        except:
            pass
        self.after(100, self.check_recorder_queue)

    def process_recording_result(self, profile):
        print(f"GUI DEBUG: Processing profile: {profile}")
        if profile and profile.get('sample_size', 0) > 0:
            
            # Show Dialog: New or Merge?
            save_window = ctk.CTkToplevel(self)
            save_window.title("Recording Finished")
            save_window.geometry("400x300")
            save_window.transient(self) # Make it modal-like
            save_window.grab_set()

            label = ctk.CTkLabel(save_window, text=f"Captured {profile['sample_size']} keystrokes.\nWPM: {profile['wpm']} | Errors: {profile['mistake_rate']:.2%}", font=("Roboto", 14))
            label.pack(pady=20)

            # Option 1: Merge into existing
            frame_merge = ctk.CTkFrame(save_window)
            frame_merge.pack(pady=10, fill="x", padx=20)
            
            lbl_merge = ctk.CTkLabel(frame_merge, text="Merge into existing style:")
            lbl_merge.pack(pady=5)
            
            # Filter out "Default" from merge options
            merge_options = [p for p in self.profile_names if "Default" not in p]
            combo_merge = ctk.CTkComboBox(frame_merge, values=merge_options)
            if merge_options:
                combo_merge.set(merge_options[0])
            else:
                combo_merge.set("No Profiles")
                combo_merge.configure(state="disabled")
            combo_merge.pack(pady=5)

            def do_merge():
                target_name = combo_merge.get()
                if not target_name or target_name == "No Profiles":
                    return
                
                # Load existing
                path = os.path.join(self.profiles_dir, target_name + ".json")
                try:
                    with open(path, 'r') as f:
                        old_profile = json.load(f)
                    
                    # Merge
                    merged = merge_profiles(old_profile, profile)
                    
                    # Save back
                    with open(path, 'w') as f:
                        json.dump(merged, f, indent=4)
                        
                    self.label_status.configure(text=f"Status: Updated '{target_name}'. Total Samples: {merged['sample_size']}")
                    
                    # Reload if currently selected
                    if self.combo_profiles.get() == target_name:
                         self.on_profile_select(target_name)
                         
                    save_window.destroy()
                except Exception as e:
                    print(f"Merge error: {e}")

            btn_merge = ctk.CTkButton(frame_merge, text="Merge & Save", command=do_merge)
            btn_merge.pack(pady=10)
            if not merge_options:
                btn_merge.configure(state="disabled")

            # Option 2: Save as New
            frame_new = ctk.CTkFrame(save_window)
            frame_new.pack(pady=10, fill="x", padx=20)

            def do_save_new():
                dialog = ctk.CTkInputDialog(text="Enter name for new style:", title="New Profile")
                name = dialog.get_input()
                if name:
                    filename = "".join(x for x in name if x.isalnum() or x in " _-")
                    if filename:
                        path = os.path.join(self.profiles_dir, f"{filename}.json")
                        with open(path, 'w') as f:
                            json.dump(profile, f, indent=4)
                        self.load_profiles_list()
                        self.combo_profiles.set(filename)
                        self.on_profile_select(filename)
                        self.label_status.configure(text=f"Status: Created '{filename}'.")
                        save_window.destroy()
            
            btn_new = ctk.CTkButton(frame_new, text="Save as New Style", fg_color="green", command=do_save_new)
            btn_new.pack(pady=10)

        else:
             self.label_status.configure(text="Status: Recording failed or no data.", text_color="orange")
        
        # Reset UI
        self.btn_record.configure(text="Record My Style", fg_color="#9C27B0")
        self.textbox.delete("0.0", "end")
        self.textbox.insert("0.0", "Recording finished. Choose an option to save.")

    def update_speed_label(self, value):
        wpm = int(value)
        self.label_speed.configure(text=f"Speed (WPM): {wpm}")
        # Send update to worker
        self.queue.put(("UPDATE_SPEED", wpm))

    def toggle_enable(self):
        if self.is_enabled:
            # Disable
            self.is_enabled = False
            self.queue.put(("DISABLE", None))
            self.btn_listen.configure(text="Enable Typing (Right Shift)", fg_color=["#3B8ED0", "#1F6AA5"])
            self.label_status.configure(text="Status: Idle")
        else:
            # Enable
            self.is_enabled = True
            text = self.textbox.get("0.0", "end-1c")
            # If match mode is active, WPM is ignored by worker anyway, but let's pass it for consistency
            wpm = int(self.slider_speed.get())
            
            # Send all current state to enable worker
            self.queue.put(("UPDATE_TEXT", text))
            self.queue.put(("UPDATE_SPEED", wpm))
            if self.profile:
                self.queue.put(("UPDATE_PROFILE", self.profile))
            self.queue.put(("ENABLE", None))
            
            self.btn_listen.configure(text="Disable Typing (Right Shift)", fg_color="green")
            self.label_status.configure(text="Status: Listener Enabled (Worker Process)...")

    def toggle_recording(self):
        if self.is_recording:
            # STOP (Manual Mode)
            self.is_recording = False
            self.recorder_queue_cmd.put("STOP")
            self.label_status.configure(text="Status: Processing recording...")
        else:
            # START (Manual Mode)
            self.is_recording = True
            self.recorder_queue_cmd.put("START")
            self.btn_record.configure(text="Stop Recording", fg_color="red")
            self.label_status.configure(text="Status: Recording... Type in the box above!", text_color="orange")
            self.textbox.delete("0.0", "end")
            self.textbox.insert("0.0", "")
            self.textbox.focus_set()

    # Wizard methods removed.
    def on_closing(self):
        self.queue.put(("KILL", None))
        self.recorder_queue_cmd.put("KILL")
        self.worker_process.terminate() 
        self.recorder_process.terminate()
        self.destroy()
