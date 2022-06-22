import os
import PySimpleGUI as sg

def guiNotify(message):
    """ Create a new window to notify user.
    """
    lines = message.split("\n")
    layout = []
    for line in lines:
        layout.append([sg.Text(line)])
    layout.append([sg.Button("OK", size=(10,1), bind_return_key=True)])
    window = sg.Window("", layout, element_justification="c")
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "OK":
            window.close()
            break

def guiSuccess():
    """ Show a success window to user.
    """
    layout = [[sg.Text("Success!")], [sg.Button("OK", size=(10,1), bind_return_key=True)]]
    window = sg.Window("",layout, element_justification="c")
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "OK":
            window.close()
            break

def guiGetDir(message):
    """ Open a window to allow user to select a directory.
    """
    # create window
    lines = message.split("\n")
    layout = []
    for line in lines:
        layout.append([sg.Text(line)])
    layout += [[sg.Text("Folder:"),
                sg.Input(size=(25, 1), enable_events=True, key="FOLDER"),
                sg.FolderBrowse()],
               [sg.Listbox(values=[], enable_events=True, size=(40, 20), key="FILE LIST")],
               [sg.Button("Continue", bind_return_key=True)]]
    valid_folder = False
    window = sg.Window('Find Files', layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break
        # check if folder is valid if selected
        elif event == "FOLDER":
            folder = values["FOLDER"]
            try:
                # get list of files in folder
                file_list = os.listdir(folder)
                valid_folder = True
            except:
                # folder does not exist
                file_list = []
                valid_folder = False
            # set up output if folder is valid
            if valid_folder:
                folder_names = [f for f in file_list
                                if os.path.isdir(folder + "/" + f)]
                file_names = [f for f in file_list
                            if os.path.isfile(folder + "/" + f)]
                # update window text
                window_text = []
                if len(folder_names) == 0 and len(file_names) == 0 and valid_folder:
                    window_text += ["EMPTY FOLDER"]
                if len(folder_names) > 0:
                    window_text += ["Folders:"] + folder_names + ["\n"]
                if len(file_names) > 0:
                    window_text += ["Files:"] + file_names
                window["FILE LIST"].update(window_text)
        # check valid folder variable when user hits submit
        elif event == "Continue":
            if valid_folder:
                window.close()
                return folder
            else:
                guiNotify("Please use a valid folder name.")