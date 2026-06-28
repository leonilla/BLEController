import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, filedialog, END, Scrollbar, RIGHT, Y, BOTH, LEFT, X
from tkinterdnd2 import TkinterDnD, DND_FILES

def handle_drop(event):
    # Windows wraps paths with spaces in curly braces, so we clean them up
    dropped_path = event.data.strip('{}')
    
    # 1. Parse 'Ignore' extensions
    ignore_raw = ignore_input.get().strip().split()
    ignore_extensions = tuple(ext.lower().lstrip('.') for ext in ignore_raw)
    
    # 2. Parse 'Include Only' extensions
    include_raw = include_input.get().strip().split()
    include_extensions = tuple(ext.lower().lstrip('.') for ext in include_raw)
    
    # Determine which mode is active based on the checkboxes
    mode_ignore = ignore_var.get()
    mode_include = include_var.get()

    if os.path.isdir(dropped_path):
        for root_dir, dirs, files in os.walk(dropped_path):
            for file in files:
                file_lower = file.lower()
                
                # Mode A: Include Only (Skip file if it DOES NOT match the list)
                if mode_include and include_extensions:
                    if not file_lower.endswith(include_extensions):
                        continue
                        
                # Mode B: Ignore (Skip file if it DOES match the list)
                elif mode_ignore and ignore_extensions:
                    if file_lower.endswith(ignore_extensions):
                        continue
                
                full_path = os.path.join(root_dir, file)
                text_field.insert(END, full_path + '\n')
    else:
        messagebox.showwarning("Not a Directory", "Please drop a folder/directory, not an individual file.")

# Mutual exclusivity logic for the checkboxes
def toggle_mode(choice):
    if choice == 'ignore':
        if ignore_var.get():
            include_var.set(False)
    elif choice == 'include':
        if include_var.get():
            ignore_var.set(False)

def clear_text():
    # Deletes everything from line 1, character 0 to the END
    text_field.delete("1.0", END)

def save_to_file():
    content = text_field.get("1.0", END).strip()
    if not content:
        messagebox.showwarning("Empty List", "There are no paths to save!")
        return
        
    # Generate a unique filename using current date and time (YYYYMMDD_HHMMSS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"manifest_{timestamp}.txt"
        
    file_path = filedialog.asksaveasfilename(
        initialfile=default_filename,
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Success", f"Paths successfully saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

# Initialize the Drag-and-Drop enabled Tkinter window (Fixed this line!)
root = TkinterDnD.Tk()
root.title("File Manifest Creator")
root.geometry("650x600")

# Variables to track checkbox states
ignore_var = tk.BooleanVar(value=True)  # Default active
include_var = tk.BooleanVar(value=False)

# --- FILTER SECTION ---
filter_frame = tk.LabelFrame(root, text=" Filter Settings ", padx=10, pady=10)
filter_frame.pack(fill=X, padx=10, pady=10)

# Row 1: Ignore Filter
ignore_row = tk.Frame(filter_frame)
ignore_row.pack(fill=X, pady=2)
tk.Label(ignore_row, text="Ignore extensions:", font=("Arial", 10), width=15, anchor="w").pack(side=LEFT)
ignore_input = tk.Entry(ignore_row, font=("Arial", 10))
ignore_input.pack(side=LEFT, fill=X, expand=True, padx=5)
ignore_input.insert(0, ".jpg .m4a")
tk.Checkbutton(ignore_row, text="Active", variable=ignore_var, command=lambda: toggle_mode('ignore')).pack(side=LEFT)

# Row 2: Include Only Filter
include_row = tk.Frame(filter_frame)
include_row.pack(fill=X, pady=2)
tk.Label(include_row, text="Include Only:", font=("Arial", 10), width=15, anchor="w").pack(side=LEFT)
include_input = tk.Entry(include_row, font=("Arial", 10))
include_input.pack(side=LEFT, fill=X, expand=True, padx=5)
include_input.insert(0, ".py .csv .txt")
tk.Checkbutton(include_row, text="Active", variable=include_var, command=lambda: toggle_mode('include')).pack(side=LEFT)


# --- DROP ZONE ---
drop_box = tk.Label(
    root, 
    text="Drag & Drop a Directory Here", 
    bg="#e0e0e0", 
    fg="#555555",
    font=("Arial", 14),
    relief="groove", 
    bd=2
)
drop_box.pack(fill=BOTH, expand=True, padx=10, pady=5)

root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', handle_drop)


# --- OUTPUT TEXT FIELD ---
text_frame = tk.Frame(root)
text_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

scrollbar = Scrollbar(text_frame)
scrollbar.pack(side=RIGHT, fill=Y)

text_field = tk.Text(text_frame, wrap="none", yscrollcommand=scrollbar.set)
text_field.pack(fill=BOTH, expand=True, side=LEFT)
scrollbar.config(command=text_field.yview)


# --- BUTTONS SECTION (SAVE & CLEAR) ---
button_frame = tk.Frame(root)
button_frame.pack(fill=X, padx=10, pady=10)

save_button = tk.Button(
    button_frame, 
    text="Save Manifest", 
    command=save_to_file,
    font=("Arial", 11, "bold"),
    bg="#4CAF50",
    fg="white",
    pady=5
)
save_button.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))

clear_button = tk.Button(
    button_frame, 
    text="Clear Text", 
    command=clear_text,
    font=("Arial", 11, "bold"),
    bg="#f44336",
    fg="white",
    pady=5
)
clear_button.pack(side=LEFT, fill=X, expand=True, padx=(5, 0))

root.mainloop()