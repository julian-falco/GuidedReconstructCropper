import os
import re
import PySimpleGUI as sg

from pyrecon.utils.gui_methods import guiGetDir, guiNotify, guiSuccess
from pyrecon.methods.update import readAll, readJSON, writeAll
from pyrecon.methods.switch import switchToCrop, switchToGlobal
from pyrecon.methods.guided_crop import guidedCrop
from pyrecon.methods.chunk_crop import chunkCrop, newChunkCrop

def getSeries():
    """ Get the series file or empty folder.
    """
    while True:
        # get series folder
        message = "Welcome to recon-cropper!\n" + \
                "Please select the folder containing your series.\n" + \
                "If you wish to create a new series, select an empty folder."
        folder = guiGetDir(message)
        # end if user hits exit button
        if not folder:
            break
        else:
            os.chdir(folder)
        # if folder is empty, create new chunked series
        if len(os.listdir(folder)) == 0:
            guiNewChunk()
            break
        else:
            # find series file
            series_found = False
            JSON_found = False
            for file in os.listdir("."):
                if file.endswith(".ser"):
                    series_found = True
                    series_name = file[:file.rfind(".ser")]
                elif file.endswith("_data.json"):
                    JSON_found = True
            if series_found: # open menu if series is found
                if not JSON_found:
                    series, tform_data = loadSeries()
                else:
                    tform_data = readJSON(series_name)
                menu(tform_data)
                break
            else: # notify user if not
                guiNotify("No series found in folder.\n" + \
                          "Select an empty folder to create a new series.")
            
def loadSeries():
    """ Load the series data from recon-cropper.
    """
    # create a loading bar for the series
    layout = [[sg.Text("Loading series...")],
              [sg.ProgressBar(100, key="PROGBAR")]]
    window = sg.Window("", layout, finalize=True)
    series, tform_data = readAll(os.getcwd(), progbar=window["PROGBAR"])
    window.close()
    return series, tform_data

def menu(tform_data):
    """ Run the main menu for recon-cropper.
    """
    # output crop fous to user
    focus = tform_data["FOCUS"]
    if focus == "GLOBAL":
        message = "This series is currently set to the uncropped images."
    else:
        focus = focus[len("LOCAL_"):]
        message = "This series is currently focused on crop: " + focus
    # create window
    layout = [[sg.Text(message, font=("", 11, "bold"))],
              [sg.Button("Switch to the uncropped series", size=(40,1), key="1")],
              [sg.Button("Switch to an object or chunk crop", size=(40,1), key="2")],
              [sg.Button("Create a new guided crop", size=(40,1), key="3")],
              [sg.Button("Divide series into chunks", size=(40,1), key="4")],
              [sg.Button("Select a new folder", size=(40,1), key="0")],
              [sg.Button("Exit", size=(15,1))]]
    window = sg.Window("Reconcropper Menu", layout, element_justification="c")
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            window.close()
            break
        elif event == "0":
            window.close()
            getSeries()
            break
        elif event == "1":
            window.close()
            guiSwitchToGlobal(focus, tform_data)
            break
        elif event == "2":
            window.close()
            guiSwitchToCrop(focus, tform_data)
            break
        elif event == "3":
            window.close()
            guiGuidedCrop(focus, tform_data)
            break
        elif event == "4":
            window.close()
            guiChunkCrop(focus, tform_data)
            break

def guiSwitchToGlobal(focus, tform_data):
    """ Generate GUI output for switching to the global series.
    """
    if focus != "GLOBAL":
        series, tform_data = loadSeries()
        # generate loading bar and perform switch
        layout = [[sg.Text("Switching to uncropped series...", key="MESSAGE")],
                        [sg.ProgressBar(100, key="PROGBAR")]]
        window = sg.Window("", layout, finalize=True)
        switchToGlobal(series, focus, tform_data, progbar=window["PROGBAR"])
        # write data to files (with loading bar)
        window["MESSAGE"].update("Writing Data to files...")
        window["PROGBAR"].update_bar(0)
        writeAll(series, tform_data, progbar=window["PROGBAR"])
        series_updated = False
        # wrap up
        window.close()
        guiSuccess()
        menu(tform_data)
    else:
        guiNotify("The series is already set to the uncropped images.")
        menu(tform_data)

def guiSwitchToCrop(focus, tform_data):
    """ Generate GUI output for switching to a crop.
    """
    # get list of existing crops
    crop_list = []
    for key in tform_data.keys():
        if key.startswith("LOCAL_"):
            crop_list.append(key[6:])
    if len(crop_list) == 0: # return to menu if no crops exist
        guiNotify("No crops for this series have been created.")
        menu(tform_data)
        return
    # gather object crops and chunk crops seperately
    coords_list = []
    obj_list = []
    coords_regex = re.compile("[0-9]+,[0-9]+")
    for crop_name in crop_list:
        if re.match(coords_regex, crop_name):
            coords_list.append(crop_name)
        else:
            if crop_name != focus:
                obj_list.append(crop_name)
    coords_list.sort()
    # if no crops found (user is on the one and only object crop)
    if len(coords_list) == 0 and len(obj_list) == 0:
        guiNotify("The series is already focused on " + focus + ".\n" + \
                  "Use the main menu to create a new crop.")
        menu(tform_data)
        return
    # set up window
    layout = [[sg.Text("Please select the crop you would like to focus on.", font=("", 12, "bold"))]]
    if len(coords_list) > 0:
        # create a grid of buttons
        rows = []
        cols = []
        for coord in coords_list:
            row, col = tuple(map(int, coord.split(",")))
            rows.append(row)
            cols.append(col)
        max_row = max(rows)
        max_col = max(cols)
        coords_column = []
        for r in range(max_row+1):
            coords_column.insert(0,[])
            for c in range(max_col+1):
                if str(c) + "," + str(r) == focus:
                    coords_column[0].append(sg.Button("X", size=(4,2), button_color="black"))
                elif str(c) + "," + str(r) in coords_list:
                    coords_column[0].append(sg.Button(str(c) + "," + str(r), size=(4,2)))
                else:
                    coords_column[0].append(sg.Button(str(c) + "," + str(r), size=(4,2), button_color="black"))
    if len(coords_list) == 0:
        # display only objects if no coords
        layout += [[sg.Combo(obj_list, key="CROP"), sg.Button("Submit")]]
    elif len(obj_list) == 0:
        # display only coords if no objects
        layout += coords_column
    else:
        # display both in columns
        obj_column = [[sg.Combo(obj_list, key="CROP")], [sg.Button("Submit")]]
        layout.append([sg.Column(obj_column),
                       sg.Column(coords_column)])
    layout.append([sg.Button("Go Back")])
    window = sg.Window("Select Crop", layout, element_justification="c")
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            window.close()
            break
        elif event == "Go Back": # go back to main menu
            window.close()
            menu(tform_data)
            break
        elif event == "Submit" or event in coords_list:
            # get the name of the crop
            if event == "Submit":
                crop_name = values["CROP"]
                crop_found = False
                for key in tform_data.keys():
                    if crop_name == key[6:]:
                        crop_found = True
                if not crop_found:
                    guiNotify("This crop does not exist.")
                    continue
                elif crop_name == focus:
                    guiNotify("You are already focused on this crop.")
                    continue
            else:
                crop_name = event
            window.close()
            # load series
            series, tform_data = loadSeries()
            # switch to global focus if not already on global
            if focus != "GLOBAL":
                layout = [[sg.Text("Switching to uncropped series to prepare...", key="MESSAGE")],
                    [sg.ProgressBar(100, key="PROGBAR")]]
                window = sg.Window("", layout, finalize=True)
                switchToGlobal(series, focus, tform_data, progbar=window["PROGBAR"])
                # set up loading bar for crop switch
                window["MESSAGE"].update("Switching to " + crop_name + "...")
                window["PROGBAR"].update_bar(0)
            else:
                layout = [[sg.Text("Switching to " + crop_name + "...", key="MESSAGE")],
                                [sg.ProgressBar(100, key="PROGBAR")]]
                window = sg.Window("", layout, finalize=True)
            switchToCrop(series, crop_name, tform_data, progbar=window["PROGBAR"])
            # write data to files
            window["MESSAGE"].update("Writing Data to files...")
            window["PROGBAR"].update_bar(0)
            writeAll(series, tform_data, progbar=window["PROGBAR"])
            # wrap up
            window.close()
            guiSuccess()
            menu(tform_data)
            break

def guiGuidedCrop(focus, tform_data):
    """ GUI output for performing a guided crop."""
    # load series
    series, tform_data = loadSeries()
    # check if images exist in directory
    images_found = True
    for section_num, section in series.sections.items():
        images_found = images_found and (os.path.isfile(tform_data["GLOBAL"][section.name]["src"]))
    # prompt user to find images if not
    if not images_found:
        while True:
            images_folder = guiGetDir("Please select the folder containing the series images.")
            if images_folder == None: # end program if user hits exit
                return
            image_files = []
            for file in os.listdir(images_folder):
                if file.endswith((".tif", ".tiff", ".png", ".jpg", ".jpeg")):
                    image_files.append(images_folder + "/" + file)
            if len(image_files) == len(series.sections):
                break
            else:
                guiNotify("The number of images in this folder does not\n" + \
                              "match the number of sections in the series.")
        # match images to the sections
        idx = 0
        images_dict = {}
        for section_num in sorted(series.sections.keys()):
            images_dict[series.sections[section_num].name] = image_files[idx]
            idx += 1
    else:
        images_dict = {}
        for section_num, section in series.sections.items():
            images_dict[section.name] = tform_data["GLOBAL"][section.name]["src"]
    # have the user enter the object name and micron radius
    layout = [[sg.Text("Name of object:"), sg.Input("", size=(19,1),key="OBJ_NAME")],
              [sg.Text("Radius around object in microns:"), sg.Input("", size=(5,1), key="RADIUS")],
              [sg.Button("Submit", bind_return_key=True), sg.Button("Go Back")]]
    window = sg.Window("Create Crop", layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            window.close()
            break
        elif event == "Go Back":
            window.close()
            menu(tform_data)
            break
        elif event == "Submit":
            valid_input = False
            obj_name = values["OBJ_NAME"]
            rad = values["RADIUS"]
            # check all inputs to make sure they're valid
            try:
                rad = float(rad)
                if obj_name:
                    valid_input = True
                    for key in tform_data.keys():
                        if obj_name == key[6:]:
                            valid_input = False
                            error_message = "A crop has already been created for this object."
            except:
                valid_input = False
                error_message = "Please enter a valid input."
            if not valid_input:
                guiNotify(error_message)
            else:
                # continue with cropping if valid
                window.close()
                # switch uncropped series
                if focus != "GLOBAL":
                    layout = [[sg.Text("Switching to uncropped series to prepare...", key="MESSAGE")],
                        [sg.ProgressBar(100, key="PROGBAR")]]
                    window = sg.Window("", layout, finalize=True)
                    switchToGlobal(series, focus, tform_data, progbar=window["PROGBAR"])
                    # set up window
                    window["MESSAGE"].update("Cropping Images...")
                    window["PROGBAR"].update_bar(0)
                else:
                    layout = [[sg.Text("Cropping Images...", key="MESSAGE")],
                                    [sg.ProgressBar(100, key="PROGBAR")]]
                    window = sg.Window("", layout, finalize=True)
                # try the crop, display error message if needed
                try:
                    guidedCrop(series, obj_name, tform_data, images_dict, rad, progbar=window["PROGBAR"])
                except Exception as e:
                    window.close()
                    guiNotify(str(e))
                    menu(tform_data)
                    break
                # write data to files
                window["MESSAGE"].update("Writing Data to files...")
                window["PROGBAR"].update_bar(0)
                writeAll(series, tform_data, progbar=window["PROGBAR"])
                # wrap up
                window.close()
                guiSuccess()
                menu(tform_data)
                break

def guiChunkCrop(focus, tform_data):
    """ GUI output for chunk crop.
    """
    # check if series has already been chunked
    if "LOCAL_0,0" in tform_data.keys():
        guiNotify("This series has already been chunked.")
        menu(tform_data)
        return
    # load series
    series, tform_data = loadSeries()
    # check if images exist in directory
    images_found = True
    for section_num, section in series.sections.items():
        images_found = images_found and (os.path.isfile(tform_data["GLOBAL"][section.name]["src"]))
    # prompt user to find images if not
    if not images_found:
        while True:
            images_folder = guiGetDir("Please select the folder containing the series images.")
            image_files = []
            for file in os.listdir(images_folder):
                if file.endswith((".tif", ".tiff", ".png", ".jpg", ".jpeg")):
                    image_files.append(file)
            if len(image_files) == len(series.sections):
                break
            else:
                guiNotify("The number of images in this folder does not",
                              "match the number of sections in the series.")
    else:
        image_files = []
        for section_num, section in series.sections.items():
            image_files.append(tform_data["GLOBAL"][section.name]["src"])
    # match images to the sections
    idx = 0
    images_dict = {}
    for section_num, section in series.sections.items():
        images_dict[section.name] = image_files[idx]
        idx += 1
    # have the user enter trows, columns, and overlap
    layout = [[sg.Text("Number of rows:", size=(15,1)), sg.Input("", size=(5,1), key="YCHUNKS")],
              [sg.Text("Number of columns:", size=(15,1)), sg.Input("", size=(5,1), key="XCHUNKS")],
              [sg.Text("Overlap between chunks in microns:"), sg.Input("", size=(5,1), key="OVERLAP")],
              [sg.Button("Submit", bind_return_key=True), sg.Button("Go Back")]]
    window = sg.Window("Chunk Crop", layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            window.close()
            break
        elif event == "Go Back":
            window.close()
            menu(tform_data)
            break
        elif event == "Submit":
            # check if user input is valid
            valid_input = False
            try:
                xchunks = int(values["XCHUNKS"])
                ychunks = int(values["YCHUNKS"])
                overlap = float(values["OVERLAP"])
                valid_input = True
            except:
                valid_input = False
            if not valid_input:
                guiNotify("Please enter a valid input.")
            else:
                window.close()
                # switch to uncropped
                if focus != "GLOBAL":
                    layout = [[sg.Text("Switching to uncropped series to prepare...", key="MESSAGE")],
                        [sg.ProgressBar(100, key="PROGBAR")]]
                    window = sg.Window("", layout, finalize=True)
                    switchToGlobal(series, focus, tform_data, progbar=window["PROGBAR"])
                    # set up window
                    window["MESSAGE"].update("Cropping Images...")
                    window["PROGBAR"].update_bar(0)
                else:
                    layout = [[sg.Text("Cropping Images...", key="MESSAGE")],
                                    [sg.ProgressBar(100, key="PROGBAR")]]
                    window = sg.Window("", layout, finalize=True)
                # perform chunk crop, display error if needed
                try:
                    chunkCrop(series, tform_data, images_dict, xchunks, ychunks, overlap, progbar=window["PROGBAR"])
                except Exception as e:
                    window.close()
                    guiNotify(str(e))
                    menu(tform_data)
                    break
                # write data to files
                window["MESSAGE"].update("Writing Data to files...")
                window["PROGBAR"].update_bar(0)
                writeAll(series, tform_data, progbar=window["PROGBAR"])
                # wrap up
                window.close()
                guiSuccess()
                menu(tform_data)
                break

def guiNewChunk():
    """GUI for creating a new chunked series.
    """
    # get the folder containing the images
    while True:
        guiNotify("This folder is empty.\nPress OK to create a new series.")
        images_folder = guiGetDir("Please select the folder containing the series images.")
        if images_folder == None: # end program if user hits exit button
            return
        # get image files
        image_files = []
        for file in os.listdir(images_folder):
            if file.endswith((".tif", ".tiff", ".png", ".jpg", ".jpeg")):
                image_files.append(images_folder + "/" + file)
        if len(image_files) > 0:
            break
        else:
            guiNotify("No images found in this folder.")
    # set up input window
    layout = [[sg.Text("New series name:", size=(15,1)), sg.Input("", size=(15,1), key="NAME")],
              [sg.Text("Number of rows:", size=(15,1)), sg.Input("", size=(5,1), key="YCHUNKS")],
              [sg.Text("Number of columns:", size=(15,1)), sg.Input("", size=(5,1), key="XCHUNKS")],
              [sg.Text("Overlap between chunks in microns:"), sg.Input("", size=(5,1), key="OVERLAP")],
              [sg.Text("Number of first section:", size=(17,1)), sg.Input("", size=(8,1), key="START")],
              [sg.Text("Section thickness:", size=(17,1)), sg.Input("", size=(8,1), key="THICKNESS")],
              [sg.Text("Calibration (optional):", size=(17,1)), sg.Input("", size=(8,1), key="CALIBRATION")],
              [sg.Button("Submit", bind_return_key=True), sg.Button("Go Back")]]
    window = sg.Window("Create New Series", layout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            window.close()
            break
        elif event == "Go Back":
            window.close()
            getSeries()
            break
        elif event == "Submit":
            # check all inputs
            valid_input = False
            try:
                xchunks = int(values["XCHUNKS"])
                ychunks = int(values["YCHUNKS"])
                overlap = float(values["OVERLAP"])
                start_section = int(values["START"])
                section_thickness = float(values["THICKNESS"])
                mic_per_pix = values["CALIBRATION"]
                if not mic_per_pix:
                    mic_per_pix = 0.00254
                    guiNotify("Calibration set to default: 0.00254\n" + \
                                  "Be sure to calibrate your series before\n" + \
                                  "tracing or importing transformations.\n" + \
                                  "Series calibrations must be done in the uncropped setting.")
                else:
                    mic_per_pix = float(mic_per_pix)
                series_name = values["NAME"]
                if series_name:
                    valid_input = True
            except:
                valid_input = False
            if not valid_input:
                guiNotify("Please enter a valid input.")
            else:
                # create the new series
                window.close()
                layout = [[sg.Text("Creating new series...", key="MESSAGE")],
                                    [sg.ProgressBar(100, key="PROGBAR")]]
                window = sg.Window("", layout, finalize=True)
                # perform chunk crop, display error if needed
                try:
                    newChunkCrop(series_name, image_files, xchunks, ychunks, overlap, start_section, section_thickness, mic_per_pix, progbar=window["PROGBAR"])
                except Exception as e:
                    window.close()
                    guiNotify(str(e))
                    getSeries()
                    break
                # wrap up, open main menu for series
                window.close()
                guiSuccess()
                series, tform_data = loadSeries()
                menu(tform_data)
                break

def startGUI():
    guiNotify("Please ensure that Reconstruct is closed.")
    getSeries()

if __name__ == "__main__":
    startGUI()
