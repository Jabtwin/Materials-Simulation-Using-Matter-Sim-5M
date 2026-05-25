import tkinter as tk
from tkinter import ttk
import sys
import os
import time

def main():
    root = tk.Tk()
    root.overrideredirect(True) # hide window borders
    
    # Calculate window size and position
    window_width = 400
    window_height = 350
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    
    root.geometry("{}x{}+{}+{}".format(window_width, window_height, x_cordinate, y_cordinate))
    
    # Configure appearance
    bg_color = "#1e1e2e"
    root.configure(bg=bg_color)
    

    
    # Optional: draw a thin border (Now in premium blue #007aff)
    border_frame = tk.Frame(root, bg="#007aff", bd=2)
    border_frame.pack(fill=tk.BOTH, expand=True)
    
    inner_frame = tk.Frame(border_frame, bg=bg_color)
    inner_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    
    # Load app icon
    try:
        from PIL import Image, ImageTk
        # Use absolute or relative path
        img_path = os.path.join(os.path.dirname(__file__), "app.ico")
        img = Image.open(img_path)
        img = img.resize((120, 120), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl_img = tk.Label(inner_frame, image=photo, bg=bg_color)
        lbl_img.image = photo
        lbl_img.pack(pady=(40, 10))
    except Exception as e:
        # If PIL is not available or icon is missing, just skip it
        pass
        
    lbl_text = tk.Label(inner_frame, text="Loading MatterSim AI...", font=("Segoe UI", 16, "bold"), fg="white", bg=bg_color)
    lbl_text.pack(pady=10)
    
    lbl_sub = tk.Label(inner_frame, text="Initializing components and engines", font=("Segoe UI", 10), fg="#a0a0b0", bg=bg_color)
    lbl_sub.pack(pady=(0, 20))
    
    # Progress bar (Now in premium blue #007aff)
    style = ttk.Style()
    style.theme_use('default')
    style.configure("TProgressbar", thickness=6, background="#007aff", troughcolor="#2b2b3b", borderwidth=0)
    progress = ttk.Progressbar(inner_frame, orient="horizontal", length=250, mode="indeterminate", style="TProgressbar")
    progress.pack(pady=10)
    progress.start(15)
    
    # Polling function to close splash
    def check_lock():
        lock_path = os.path.join(os.path.dirname(__file__), "splash.lock")
        if not os.path.exists(lock_path):
            root.destroy()
        else:
            root.after(200, check_lock)
            
    # Check for the lock file periodically
    root.after(500, check_lock)
    
    # Failsafe: destroy after 30 seconds if main app fails
    root.after(30000, root.destroy)

    root.mainloop()

if __name__ == "__main__":
    main()
