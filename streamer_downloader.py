import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import threading
import queue
import os

class YtDownloaderApp(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.parent = parent
        self.cookie_file_path = ""
        self.download_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.is_downloading = False
        self.log_queue = queue.Queue()
        
        # --- New Feature Variables ---
        self.merge_var = tk.BooleanVar(value=False) # Default to NOT merging
        self.placeholder_text = "Paste one or more YouTube URLs or playlist URLs here..."

        self.create_widgets()
        self.periodic_log_check()

    def on_entry_focus_in(self, event):
        """Function to handle focus in the URL entry box."""
        if self.url_input.get("1.0", "end-1c") == self.placeholder_text:
            self.url_input.delete("1.0", tk.END)
            self.url_input.config(fg='black') # Or your theme's default text color

    def on_entry_focus_out(self, event):
        """Function to handle focus out of the URL entry box."""
        if not self.url_input.get("1.0", "end-1c"):
            self.url_input.insert("1.0", self.placeholder_text)
            self.url_input.config(fg='grey')

    def create_widgets(self):
        # --- Input and Queue Controls ---
        input_frame = ttk.LabelFrame(self, text="1. Add Videos", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        self.url_input = tk.Text(input_frame, height=5, fg='grey')
        self.url_input.pack(fill=tk.X, expand=True, pady=(0, 5))
        # Bind events for smart placeholder
        self.url_input.bind("<FocusIn>", self.on_entry_focus_in)
        self.url_input.bind("<FocusOut>", self.on_entry_focus_out)
        self.on_entry_focus_out(None) # Set initial placeholder state

        add_button = ttk.Button(input_frame, text="Add to Queue", command=self.add_to_queue)
        add_button.pack(fill=tk.X)

        # --- Queue Listbox ---
        queue_frame = ttk.LabelFrame(self, text="2. Download Queue", padding="10")
        queue_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        # ... (Rest of queue frame is unchanged)
        listbox_container = ttk.Frame(queue_frame)
        listbox_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.queue_listbox = tk.Listbox(listbox_container, selectmode=tk.SINGLE)
        self.queue_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.queue_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.queue_listbox.config(yscrollcommand=scrollbar.set)
        queue_controls_frame = ttk.Frame(queue_frame)
        queue_controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, anchor='n')
        btn_up = ttk.Button(queue_controls_frame, text="Up", command=lambda: self.move_item(-1))
        btn_up.pack(pady=2, fill=tk.X)
        btn_down = ttk.Button(queue_controls_frame, text="Down", command=lambda: self.move_item(1))
        btn_down.pack(pady=2, fill=tk.X)
        btn_remove = ttk.Button(queue_controls_frame, text="Remove", command=self.remove_item)
        btn_remove.pack(pady=2, fill=tk.X)
        btn_clear = ttk.Button(queue_controls_frame, text="Clear", command=self.clear_queue)
        btn_clear.pack(pady=20, fill=tk.X)


        # --- Settings and Actions ---
        settings_frame = ttk.LabelFrame(self, text="3. Settings & Download", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)

        cookie_btn = ttk.Button(settings_frame, text="Select cookies.txt", command=self.select_cookie_file)
        cookie_btn.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.cookie_label = ttk.Label(settings_frame, text="No cookie file selected.")
        self.cookie_label.grid(row=0, column=1, sticky="w", padx=5)
        
        download_btn = ttk.Button(settings_frame, text="Select Download Folder", command=self.select_download_folder)
        download_btn.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.download_label = ttk.Label(settings_frame, text=f"Saving to: {self.download_path}", wraplength=450)
        self.download_label.grid(row=1, column=1, sticky="w", padx=5)
        
        # --- NEW MERGE CHECKBOX ---
        merge_check = ttk.Checkbutton(settings_frame, text="Merge video and audio into a single file", variable=self.merge_var)
        merge_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        settings_frame.grid_columnconfigure(1, weight=1)

        self.start_button = ttk.Button(self, text="Start Download", command=self.start_download_thread, style="Accent.TButton")
        self.start_button.pack(fill=tk.X, pady=10, ipady=5)

        # --- Log Window ---
        log_frame = ttk.LabelFrame(self, text="Log Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = tk.Text(log_frame, state='disabled', wrap='word', bg="#fdfdfd", fg="#333333", font=("Courier New", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    # ... (Most other methods are unchanged)
    def add_to_queue(self):
        # Prevent adding the placeholder text to the queue
        text_content = self.url_input.get("1.0", tk.END).strip()
        if text_content == self.placeholder_text:
            return
        urls = text_content.split('\n')
        for url in urls:
            if url.strip():
                self.queue_listbox.insert(tk.END, url.strip())
        self.on_entry_focus_out(None) # Reset placeholder after adding

    def process_queue(self):
        queue_items = self.queue_listbox.get(0, tk.END)
        for i, url in enumerate(queue_items):
            self.parent.after(0, lambda idx=i: self.queue_listbox.selection_clear(0, tk.END) or self.queue_listbox.selection_set(idx))
            self.log(f"--- Starting download for: {url} ---")
            
            # --- DYNAMIC YDL_OPTS BASED ON MERGE CHECKBOX ---
            ydl_opts = {
                'outtmpl': os.path.join(self.download_path, '%(title)s - [%(id)s].%(ext)s'),
                'cookiefile': self.cookie_file_path,
                'progress_hooks': [self.my_hook],
                'logger': self.MyLogger(self),
                'noplaylist': False,
                'ignoreerrors': True,
            }

            if self.merge_var.get():
                # Merge into single file
                self.log("[OPTIONS] Merge Mode enabled. Creating single output file.")
                ydl_opts['format'] = 'bv*+ba/b'
            else:
                # Keep separate files (the new default)
                self.log("[OPTIONS] Split Mode enabled. Saving separate video and audio files.")
                ydl_opts['format'] = 'bv*,ba' # The comma is the key
                ydl_opts['keepvideo'] = True  # Prevents deleting the separate streams

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self.log(f"--- Finished processing: {url} ---")
            except Exception as e:
                self.log(f"!!! An unexpected error occurred: {e} !!!")
        self.parent.after(0, self.download_finished)


    # --- Unchanged Helper Methods Below ---

    def select_cookie_file(self):
        path = filedialog.askopenfilename(title="Select your cookies.txt file", filetypes=[("Text files", "*.txt")])
        if path:
            self.cookie_file_path = path
            self.cookie_label.config(text=f"Using: ...{os.path.basename(path)}")
            self.log(f"Cookie file set to: {self.cookie_file_path}")

    def select_download_folder(self):
        path = filedialog.askdirectory(title="Select where to save videos")
        if path:
            self.download_path = path
            self.download_label.config(text=f"Saving to: {self.download_path}")
            self.log(f"Download folder set to: {self.download_path}")

    def move_item(self, direction):
        selected_indices = self.queue_listbox.curselection()
        if not selected_indices: return
        idx = selected_indices[0]
        if (direction == -1 and idx == 0) or (direction == 1 and idx == self.queue_listbox.size() - 1): return
        text = self.queue_listbox.get(idx)
        self.queue_listbox.delete(idx)
        self.queue_listbox.insert(idx + direction, text)
        self.queue_listbox.selection_set(idx + direction)

    def remove_item(self):
        selected_indices = self.queue_listbox.curselection()
        if selected_indices: self.queue_listbox.delete(selected_indices[0])
            
    def clear_queue(self):
        self.queue_listbox.delete(0, tk.END)

    def log(self, message):
        self.log_queue.put(message)

    def update_log_widget(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, message + '\n')
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            
    def periodic_log_check(self):
        self.update_log_widget()
        self.after(100, self.periodic_log_check)

    def start_download_thread(self):
        if self.is_downloading:
            messagebox.showwarning("Busy", "A download is already in progress.")
            return
        if not self.cookie_file_path:
            messagebox.showerror("Error", "Please select a cookies.txt file first.")
            return
        if self.queue_listbox.size() == 0:
            messagebox.showinfo("Info", "Queue is empty. Add some URLs first.")
            return
        
        self.is_downloading = True
        self.start_button.config(text="Downloading...", state='disabled')
        download_thread = threading.Thread(target=self.process_queue, daemon=True)
        download_thread.start()

    def download_finished(self):
        self.is_downloading = False
        self.start_button.config(text="Start Download", state='normal')
        self.queue_listbox.delete(0, tk.END)
        self.log("====== All downloads complete! Queue Cleared. ======")
        messagebox.showinfo("Success", "All items in the queue have been processed.")

    def my_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            self.log(f" > Downloading: {d['filename']} | {percent} at {speed}, ETA: {eta}")
        elif d['status'] == 'finished':
            # This message now depends on the mode
            if not self.merge_var.get() and d.get('keepvideo'):
                 self.log(f" > Download of stream complete.")
            else:
                 self.log(f" > Download finished. Now merging formats if needed...")
        elif d['status'] == 'error':
            self.log(f" > ERROR: {d.get('error', 'Unknown yt-dlp error')}")
            
    class MyLogger:
        def __init__(self, app_instance): self.app = app_instance
        def debug(self, msg):
            if not msg.startswith('[debug] '): self.info(msg)
        def info(self, msg): self.app.log(f"{msg}")
        def warning(self, msg): self.app.log(f"[WARNING] {msg}")
        def error(self, msg): self.app.log(f"[ERROR] {msg}")

if __name__ == "__main__":
    root = None
    try:
        from ttkthemes import ThemedTk
        # "breeze" is a clean, modern, light theme. Great choice.
        root = ThemedTk(theme="breeze")
    except ImportError:
        print("ttkthemes not found, using default theme. For a better look, run: pip install ttkthemes")
        root = tk.Tk()

    root.title("Streamer's VOD Downloader")
    root.geometry("800x700") # Increased height slightly for the new checkbox
    
    app = YtDownloaderApp(root, padding="10")
    app.pack(fill=tk.BOTH, expand=True)
    
    style = ttk.Style(root)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    root.mainloop()