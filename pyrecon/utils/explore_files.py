import tkinter as tk
from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory

def findFile(file_label="All Files", file_type = "*"):
    """ Open file explorer to select a single file.
    """
    # create tkinter object without displaying extra window
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    # open file explorer to select file
    new_file = askopenfilename(title="Select File",
                               filetypes=((file_label, "*." + file_type), ("All Files","*.*")))
    if not new_file:
        raise Exception("No file selected.")
    return new_file

def findFiles(file_label="All Files", file_type = "*"):
    """ Open file explorer to select multiple files.
    """
    # create tkinter object without displaying extra window
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    # open file explorer to select files
    new_files = askopenfilenames(title="Select File",
                               filetypes=((file_label, "*." + file_type), ("All Files","*.*")))
    if not new_files:
        raise Exception("No files selected.")
    return new_files

def findDir():
    """ Open file explorer to select a directory/folder.
    """
    # create tkinter object without displaying extra window
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    # open file explorer to select directory
    new_dir = askdirectory(title="Select Folder")
    if not new_dir: # raise exception if user does not select folder
        raise Exception("No directory was selected.")
    return new_dir