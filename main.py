
from gui import TyperAPP
import sys
import os

# Redirect stdout/stderr to a log file in home directory
log_path = os.path.join(os.path.expanduser("~"), "typer_debug_log.txt")
sys.stdout = open(log_path, 'w', buffering=1) # Line buffering
sys.stderr = sys.stdout

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support() # Required for PyInstaller/Multiprocessing
    
    print("DEBUG: Starting App...")
    try:
        app = TyperAPP()
        print("DEBUG: App initialized. Starting mainloop...")
        app.mainloop()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        # Try to show a native error message if possible
        try:
            import tkinter.messagebox
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            tkinter.messagebox.showerror("Critical Error", f"App crashed:\n{e}")
        except:
            pass
