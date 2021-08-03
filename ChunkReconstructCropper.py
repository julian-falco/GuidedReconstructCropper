# FUNCTIONS BLOCK
    
def findBounds(fileName, obj):
    """Finds the bounds of a specified object on a single trace file."""
    
    # open trace file, read lines, and close
    sectionFile = open(fileName, 'r')
    lines = sectionFile.readlines()    
    sectionFile.close()

    # get the domain transformation
    domainIndex = 0
    line = lines[domainIndex]
    
    # check for domain in the text to find domain origin index
    while not '"domain1"' in line:
        domainIndex += 1
        line = lines[domainIndex]

    # grab xcoef transformation
    xcoef = [float(x) for x in lines[domainIndex-4].replace('"',"").split()[1:4]]

    # grab ycoef transformation
    ycoef = [float(y) for y in lines[domainIndex-3].replace('">',"").split()[1:4]]

    # convert to transformation matrix
    domain_trans = coefToMatrix(xcoef, ycoef)
    
    # create variables: min for points with and without inverse domain transformation
    xmin = 0
    xmin_idomain = 0
    xmax = 0
    xmax_idomain = 0
    ymin = 0
    ymin_idomain = 0
    ymax = 0
    ymax_idomain = 0
    
    # recording: set to True whenever the points in the file are being recorded
    recording = False
    
    for lineIndex in range(len(lines)):
        
        # grab line
        line = lines[lineIndex]
        
        # if data points are being recorded from the trace file...
        if recording:
            
            # the first point starts with "points=" in the text file; remove this part
            if firstLine:
                line = line.replace('points="', '')
                firstLine = False
            
            #remove commas
            line = line.replace(',', '')
            
            # split line into x and y coords
            coords = line.split()
            
            # check if there are still points there and add to sum (with matrix transformation)
            if len(coords) == 2:
                
                # set up points and transformation matrix
                coords_mat = np.array([[float(coords[0])],
                                       [float(coords[1])],
                                       [1]]) # matrix for the point
                trans_mat = coefToMatrix(xcoef, ycoef) # transformation 
                inv_domain_trans = np.linalg.inv(domain_trans) # inverse domain transformation

                trans_coords = np.matmul(trans_mat, coords_mat) # point fixed in reconstruct space (to return)
                trans_coords_idomain = np.matmul(inv_domain_trans, trans_coords) # point fixed to the image (to check)

                # if no points recorded yet, set min and maxes
                if xmin == 0 and xmax == 0 and ymin == 0 and ymax == 0:
                    xmin = trans_coords[0][0]
                    xmax = trans_coords[0][0]
                    ymin = trans_coords[1][0]
                    ymax = trans_coords[1][0]
                    xmin_idomain = trans_coords_idomain[0][0]
                    xmax_idomain = trans_coords_idomain[0][0]
                    ymin_idomain = trans_coords_idomain[1][0]
                    ymax_idomain = trans_coords_idomain[1][0]

                # otherwise, check for min and max values for both x and y
                # points fixed to the image are checked
                else:
                    if trans_coords_idomain[0][0] < xmin_idomain:
                        xmin = trans_coords[0][0]
                        xmin_idomain = trans_coords_idomain[0][0]
                    if trans_coords_idomain[0][0] > xmax_idomain:
                        xmax = trans_coords[0][0]
                        xmax_idomain = trans_coords_idomain[0][0]
                    if trans_coords_idomain[1][0] < ymin_idomain:
                        ymin = trans_coords[1][0]
                        ymin_idomain = trans_coords_idomain[1][0]
                    if trans_coords_idomain[1][0] > ymax_idomain:
                        ymax = trans_coords[1][0]
                        ymax_idomain = trans_coords_idomain[1][0]
            
            # stop recording otherwise
            else:
                recording = False
            
        # if not recording data points...
        else:
            
            # check for object name in the line
            if ('"' + obj + '"') in line:
                recording = True
                firstLine = True
                
                # backtrack through the trace file to find the xcoef and ycoef
                xcoefIndex = lineIndex
                while not ("xcoef" in lines[xcoefIndex]):
                    xcoefIndex -= 1
                
                # set the xcoef and ycoef
                xcoef = [float(x) for x in lines[xcoefIndex].split()[1:4]]
                ycoef = [float(y) for y in lines[xcoefIndex+1].split()[1:4]]
    
    # if the trace is not found in the section
    if xmin == 0 and xmax == 0 and ymin == 0 and ymax == 0:
        return None
    
    # return bounds (fixed to Reconstruct space)
    return xmin, xmax, ymin, ymax



def fillInBounds(bounds_dict):
    """Fills in bounds data where object doesn't exist with bounds data from previous sections."""
    
    # if the first section(s) do not have the object, then fill it in with first object instance
    firstInstanceFound = False
    prevBounds = None
    for bounds in bounds_dict:
        if bounds_dict[bounds] != None and not firstInstanceFound:
            prevBounds = bounds_dict[bounds]
            firstInstanceFound = True
    
    # set any bounds points that are None to the previous bounds
    for bounds in bounds_dict:
        if bounds_dict[bounds] == None:
            bounds_dict[bounds] = prevBounds
        prevBounds = bounds_dict[bounds]
    
    return bounds_dict



def getSectionInfo(fileName):
    """Gets the transformation, magnification, and image source from a single trace file."""
    
    # open trace file, read lines, and close
    traceFile = open(fileName, "r")
    lines = traceFile.readlines()
    traceFile.close()
    
    # set up iterator
    domainIndex = 0
    line = lines[domainIndex]
    
    # check for domain in the text to find domain origin index
    while not '"domain1"' in line:
        domainIndex += 1
        line = lines[domainIndex]

    # grab xcoef transformation
    xcoef = [float(x) for x in lines[domainIndex-4].replace('"',"").split()[1:4]]

    # grab ycoef transformation
    ycoef = [float(y) for y in lines[domainIndex-3].replace('">',"").split()[1:4]]

    # get magnification and image source
    mag = float(lines[domainIndex-2].split('"')[1])
    src = lines[domainIndex-1].split('"')[1]    

    return xcoef, ycoef, mag, src

    
def getSeriesInfo(fileName):
    """Return the series name and number of sections."""

    # get only the name
    seriesName = fileName.replace(".ser", "")
    
    # find out how many sections there are
    sectionNums = []
    
    # search each file in the folder that ends with a number
    for file in os.listdir():
        try:
            sectionNums.append(int(file[file.rfind(".")+1:]))
        except:
            pass

    # sort the section numbers so they are in order
    sectionNums.sort()

    return seriesName, sectionNums


def switchToOriginal(seriesName, objName):
    """Switch focus to a cropped series from the original."""

    # check for transformations that deviate from the original alignment
    iDtrans_dict = checkForRealignment(seriesName, objName)

    # open and read the transformation file
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    # create new transformation file
    newLocalTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "w")

    # store the new transformations and grab shifts for each section
    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1]) # get section number
        elif "xshift" in line:
            xshift_pix = int(line.split()[1]) # get shifted origin
        elif "yshift" in line:
            yshift_pix = int(line.split()[1]) # get shifted origin

        # transformation all the traces so that they match the original and save transformation data for cropped version    
        elif "Dtrans" in line:
            transformAllTraces(seriesName + "." + str(sectionNum),
                               iDtrans_dict[sectionNum], # transform all the traces by this matrix
                               -xshift_pix, -yshift_pix, "") # additionally, move domain and change image source
            
            # store the transformation matrix going from original to cropped
            Dtrans = np.linalg.inv(iDtrans_dict[sectionNum])
            line = "Dtrans: "
            line += str(Dtrans[0,0]) + " "
            line += str(Dtrans[0,1]) + " "
            line += str(Dtrans[0,2]) + " "
            line += str(Dtrans[1,0]) + " "
            line += str(Dtrans[1,1]) + " "
            line += str(Dtrans[1,2]) + "\n"
                
        newLocalTrans.write(line)

    # transform all of the z-traces
    transformZtraces(seriesName + ".ser", iDtrans_dict)

    newLocalTrans.close()
            

def switchToCrop(seriesName, objName):
    """Switch focus to an original series from a cropped one."""
    
    # open transformation files
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    # get section numbers
    sectionNums = []
    for line in lines:
        if "Section" in line:
            sectionNums.append(int(line.split()[1]))
    
    # save current alignment on original
    saveOriginalTransformations(seriesName, sectionNums)

    # store transformations (for z-traces)
    Dtrans_dict = {}

    # grab transformation data from each of the files
    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1]) # get the section number
        elif "xshift" in line:
            xshift_pix = int(line.split()[1]) # get shifted origin
        elif "yshift" in line:
            yshift_pix = int(line.split()[1]) # get shifted origin

        # transform all traces to saved aligment, shift origin, and change image source
        elif "Dtrans" in line:
            
            # create the new alignment matrix
            Dtrans = [float(z) for z in line.split()[1:7]]
            DtransMatrix = [[Dtrans[0],Dtrans[1],Dtrans[2]],
                                 [Dtrans[3],Dtrans[4],Dtrans[5]],
                                 [0,0,1]]

            # transform all the traces by the Dtrans matrix
            transformAllTraces(seriesName + "." + str(sectionNum),
                               DtransMatrix, # shift all traces by this matrix
                               xshift_pix, yshift_pix, objName) # shift the origins change image source

            # add transformation to dictionary
            Dtrans_dict[sectionNum] = DtransMatrix

    # transform all of the z-traces
    transformZtraces(seriesName + ".ser", Dtrans_dict)
        
    
def checkForRealignment(seriesName, objName):
    """Check for differences in domain alignment between cropped and original series."""

    # open the two transformation files
    origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "r")
    localTransFile = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")

    # store trasnformations
    iDtransList = {}

    # read through local and original transformations simultaneously
    for localLine in localTransFile.readlines():
        if "Section" in localLine:
            origTransFile.readline() # skip line in original file
            sectionNum = int(localLine.split()[1]) # get the section number
            
            # get new domain transformation info for this section
            sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))
            local_xcoef = sectionInfo[0]
            local_ycoef = sectionInfo[1]
        
        elif "xshift" in localLine:
            xshift = int(localLine.split()[1]) * sectionInfo[2] # get origin shift

            # get original domain transformation info for this section
            origLine = origTransFile.readline() 
            orig_xcoef = [float(x) for x in origLine.split()[1:4]]
            
        elif "yshift" in localLine:
            yshift = int(localLine.split()[1]) * sectionInfo[2] # get origin shift

            # get original domain transformation info for this section
            origLine = origTransFile.readline()
            orig_ycoef = [float(y) for y in origLine.split()[1:4]]

        # check for realignment using the two matrices
        elif "Dtrans" in localLine:
            
            # set up the two matrices
            local_matrix = coefToMatrix(local_xcoef, local_ycoef) # new transformation
            orig_matrix = coefToMatrix(orig_xcoef, orig_ycoef) # original transformation

            # transform the shifted origin by ONLY the shear/stretch components of the new transformation
            transformedShiftCoords = np.matmul(local_matrix[:2,:2], [[xshift],[yshift]])

            # cancel out xshift and yshift from new transformation to match original
            local_matrix[0][2] -= transformedShiftCoords[0][0]
            local_matrix[1][2] -= transformedShiftCoords[1][0]
            
            # get the "difference" between the two matrices and store the result
            iD_matrix = np.matmul(orig_matrix, np.linalg.inv(local_matrix))
            iDtransList[sectionNum] = iD_matrix
        
    origTransFile.close()
    localTransFile.close()

    return iDtransList


def transformAllTraces(fileName, transformation, xshift_pix, yshift_pix, objName):
    """Multiply all of the traces on a section by a transformation matrix; also chang the image domain and source."""

    # get section info
    sectionInfo = getSectionInfo(fileName)
    sectionNum = int(fileName[fileName.rfind(".")+1:])
    
    # check if transformation is needed
    transformation = np.array(transformation)
    noTrans = np.array([[1,0,0],[0,1,0],[0,0,1]])
    needsTransformation = not (np.round(transformation, decimals = 8) == noTrans).all()

    # make the domain transformation matrix
    existingDomainTrans = coefToMatrix(sectionInfo[0],sectionInfo[1]) # get existing domain transformation

    # transform the shifted origin by ONLY shear/stretch component of transformation
    transformedShiftCoords = np.matmul(existingDomainTrans[:2,:2],
                                       [[xshift_pix*sectionInfo[2]],[yshift_pix*sectionInfo[2]]])
    transformedShiftCoords = np.matmul(transformation[:2,:2], transformedShiftCoords)

    # add the transformed shifts to the matrix that will transform the domain
    domainTransformation = transformation.copy()
    domainTransformation[0][2] += transformedShiftCoords[0][0]
    domainTransformation[1][2] += transformedShiftCoords[1][0]
    
    # open and read the section file    
    sectionFile = open(fileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()

    # check for domain in the text to find domain origin index
    domainIndex = 0
    line = lines[domainIndex]
    while not '"domain1"' in line:
        domainIndex += 1
        line = lines[domainIndex]

    # create the new section file
    newSectionFile = open(fileName, "w")

    # read through the file
    for i in range(len(lines)):
        line = lines[i]

        # make sure the dimension is set to three
        if '<Transform dim="0"' in line:
            line = line.replace("0", "3")

        # if iterator is on the domain xcoef line
        elif i == domainIndex - 4:
            
            # gather the matrices and multiply them by the transformation matrix
            xcoef = [float(x) for x in line.split()[1:4]]
            ycoef = [float(y) for y in lines[i+1].split()[1:4]]
            newMatrix = np.linalg.inv(np.matmul(domainTransformation, coefToMatrix(xcoef, ycoef)))

            # set up strings for both xcoef and ycoef to write to file
            
            xcoef_line = ' xcoef=" '
            xcoef_line += str(newMatrix[0,2]) + " "
            xcoef_line += str(newMatrix[0,0]) + " "
            xcoef_line += str(newMatrix[0,1]) + " "
            xcoef_line += '0 0 0"\n'

            ycoef_line = ' ycoef=" '
            ycoef_line += str(newMatrix[1,2]) + " "
            ycoef_line += str(newMatrix[1,0]) + " "
            ycoef_line += str(newMatrix[1,1]) + " "
            ycoef_line += '0 0 0">\n'

            line = xcoef_line

        # if iterator is on domain ycoef line
        elif i == domainIndex - 3:

            # write line that was set in previous elif statement
            line = ycoef_line

        # cif iterator is on the image source line
        elif i == domainIndex - 1:
            imageFile = line.split('"')[1] # get the current image source
            if "/" in imageFile and objName == "": # if image source is focused on a crop and switching to original
                imageFile = imageFile[imageFile.find("/")+1:]
            else: # if image source is set to original and switching to a crop
                imageFile = seriesName + "_" + objName + "/" + imageFile
                
            line = ' src="' + imageFile + '" />\n'

        # if non-identity transformation and iterator is on xcoef that isn't domain
        elif needsTransformation and "xcoef" in line:
            
            # gather the matrices and multiply them by the transformation matrix
            xcoef = [float(x) for x in line.split()[1:4]]
            ycoef = [float(y) for y in lines[i+1].split()[1:4]]
            newMatrix = np.linalg.inv(np.matmul(transformation, coefToMatrix(xcoef, ycoef)))

            # set up strings for both xcoef and ycoef to write to file
            
            xcoef_line = ' xcoef=" '
            xcoef_line += str(newMatrix[0,2]) + " "
            xcoef_line += str(newMatrix[0,0]) + " "
            xcoef_line += str(newMatrix[0,1]) + " "
            xcoef_line += '0 0 0"\n'

            ycoef_line = ' ycoef=" '
            ycoef_line += str(newMatrix[1,2]) + " "
            ycoef_line += str(newMatrix[1,0]) + " "
            ycoef_line += str(newMatrix[1,1]) + " "
            ycoef_line += '0 0 0">\n'

            line = xcoef_line

        # if non-identity transformation and iterator is on ycoef that isn't domain
        elif needsTransformation and "ycoef" in line:

            # write line that was set up in previous elif statement
            line = ycoef_line

        newSectionFile.write(line)

    newSectionFile.close()

def transformZtraces(fileName, transformation_dict):
    """Transform all of the ztraces in a series file."""

    # read all of the lines in the series file
    seriesFile = open(fileName, "r")
    lines = seriesFile.readlines()
    seriesFile.close()

    # create new series file
    newSeriesFile = open(fileName, "w")

    # iterate through series file
    recording = False
    for line in lines:

        # if at end of points while recording, stop recording
        if recording and line.strip() == '"/>':
            recording = False

        # transform points if recording
        if recording:

            # split line to get info
            split_line = line.replace('points="',"").split()
            x_coord = float(split_line[0])
            y_coord = float(split_line[1])
            sectionNum = int(split_line[2].replace(",",""))

            # transform coordinates
            coords = [[x_coord],[y_coord],[1]]
            trans_coords = np.matmul(transformation_dict[sectionNum], coords)

            # replace old with new coordinates
            line = line.replace(split_line[0], str(round(trans_coords[0][0],4)))
            line = line.replace(split_line[1], str(round(trans_coords[1][0],4)))       

        # if iterator reaches beginning of Ztrace
        if line.startswith("<ZContour name="):
            recording = True

        newSeriesFile.write(line)

def coefToMatrix(xcoef, ycoef):
    """Turn a set of x and y coef into a transformation matrix."""
    
    return np.linalg.inv(np.array([[xcoef[1], xcoef[2], xcoef[0]],
                       [ycoef[1], ycoef[2], ycoef[0]],
                       [0, 0, 1]]))


def getCropFocus(sectionFileName, seriesName):
    """Find the current crop focus based on the image source of the first section."""

    # open the section file
    sectionFile = open(sectionFileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()

    # find the image file
    lineIndex = 0
    while 'src="' not in lines[lineIndex]:
        lineIndex += 1
    imageFile = lines[lineIndex].split('"')[1]

    # analyze the image file name
    if "/" in imageFile:
        folder = imageFile.split("/")[0]
        cropFocus = folder[folder.find(seriesName)+len(seriesName)+1:]
    else:
        cropFocus = ""

    return cropFocus


def saveOriginalTransformations(seriesName, sectionNums):
    """Save the current set of trasnformations to the ORIGINAL_TRANSFORMATIONS.txt file"""

    # open the original transformations file
    transformationsFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")

    for sectionNum in sectionNums:

        # get existing transformations
        sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))

        # turn existing transformation into strings
        xcoef_str = ""
        for x in sectionInfo[0]:
            xcoef_str += str(x) + " "
        ycoef_str = ""
        for y in sectionInfo[1]:
            ycoef_str += str(y) + " "

        # write the new xcoef and ycoef to the file
        transformationsFile.write("Section " + str(sectionNum) + "\n"
                                  "xcoef: " + xcoef_str + "\n" +
                                  "ycoef: " + ycoef_str + "\n")
    transformationsFile.close()


def intInput(inputStr):
    """Force user to give an integer input."""
    
    isInt = False
    while not isInt:
        try:
            num = int(input(inputStr))
            isInt = True
        except ValueError:
            print("Please enter a valid integer.")
    return num

def floatInput(inputStr):
    """Force user to give a float input."""
    
    isFloat = False
    while not isFloat:
        try:
            num = float(input(inputStr))
            isFloat = True
        except ValueError:
            print("Please enter a valid number.")
    return num

def ynInput(inputStr):
    """Force user to give y/n input."""
    
    response = input(inputStr)
    while response != "y" and response != "n":
        print("Please enter y or n.")
        response = input(inputStr)
    if response == "y":
        return True
    return False


# MAIN P1: Ensuring that modules are installed in the correct place

try:
    print("Getting modules...")

    # default modules
    import sys
    import os

    # boolean to keep track if module needs to be imported
    needs_import = False

    # find the site-packages folder to put the modules into
    for p in sys.path:
        if p.endswith("site-packages"):
            module_dir = p
            
    # raise an error if there is no site-packages folder
    if not module_dir:
        raise Exception("There is no site-packages folder located on the path.")

    # try to import numpy
    try:
        import numpy as np
        numpy_bat = ""
    except ModuleNotFoundError:
        # if not found, inform user and set up batch text
        needs_import = True
        print("\nThe numpy module is not found in the current path.")
        numpy_bat = "pip install numpy --target " + module_dir + "\n"

    # try to import tkinter (should already be a part of python)
    try:
        from tkinter import *
        from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
        tkinter_bat = ""
    except ModuleNotFoundError:
        # if not found, inform user and set up batch text
        needs_import = True
        print("\nThe tkinter module is not found in the current path.")
        tkinter_bat = "pip install tk --target " + module_dir + "\n"

    # try to import Pillow
    try:
        from PIL import Image as PILImage
        PILImage.MAX_IMAGE_PIXELS = None # turn off image size restriction
        Pillow_bat = ""
    except ModuleNotFoundError:
        # if not found, inform user and set up batch text
        needs_import = True
        print("\nThe Pillow module is not found in the current path.")
        Pillow_bat = "pip install Pillow --target " + module_dir + "\n"

    # do nothing if all modules found
    if not needs_import:
        print("\nAll required modules have been successfully located.")

    # install modules that were not found
    else:

        #ask user if they want to direct the program to the modules
        directing = ynInput("Would you like to find the site-packages folder containing the required modules? (y/n): ")
        
        if directing:
            site_packages_dir = input("Please paste the path for the site-packages directory containing the required modules.")
            sys.path.append(site_packages_dir)

            # try to import all of the required modules again
            try:
                import numpy as np
                from tkinter import *
                from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
                from PIL import Image as PILImage
                PILImage.MAX_IMAGE_PIXELS = None # turn off image size restriction
                print("Modules have been found.")

            # if given folder still doesn't contain module, download them
            except ModuleNotFoundError:
                print("Modules were not found in provided folder.")
                directing = False
            
        # download modules if user does not locate them
        if not directing:
            input("\nPress enter to download the modules.")
            
            # create the batch file
            bat = open("InstallModules.bat", "w")
            bat.write(numpy_bat)
            bat.write(tkinter_bat)
            bat.write(Pillow_bat)
            bat.close()

            # run the batch file with subprocess module
            print("\nOpening Command Prompt to install required modules...")    
            import subprocess
            subprocess.call(["InstallModules.bat"])

            # delete the batch
            os.remove("InstallModules.bat")

            # import the modules that were just installed
            if numpy_bat:
                import numpy as np
            if tkinter_bat:
                from tkinter import *
                from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
            if Pillow_bat:
                from PIL import Image as PILImage
                PILImage.MAX_IMAGE_PIXELS = None

            print("\nThe necessary modules have been installed.")

except Exception as e:
    print(e)


# MAIN P2: Cropping and user interface for switching crops
    
try:

    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)

    # change working directory to file location and output working directory
    os.chdir(application_path)
    print("\nCurrent working directory: " + os.getcwd())

    change = ynInput("Would you like to change the working directory? (y/n): ")

    # prompt user to select new directory if desired
    if change:
        input("\nPress enter to select the new working directory.")

        # create tkinter object but don't display extra window
        root = Tk()
        root.attributes("-topmost", True)
        root.withdraw()

        # open file explorer to select new working directory
        os.chdir(askdirectory(title="Select Folder"))

    # locate the series file and get series name if found
    print("\nLocating series file...")
    fileName = ""
    for file in os.listdir("."):
        if file.endswith(".ser"):
            fileName = str(file)

    # prompt user to switch crops if there is an existing series file
    if fileName:

        # gather series info data
        seriesName, sectionNums = getSeriesInfo(fileName)

        # find and output the current crop focus
        cropFocus = getCropFocus(seriesName + "." + str(sectionNums[0]), seriesName)
        if cropFocus:
            print("This series is currently focused on: " + cropFocus)
        else:
            print("This series is currently set to the original set of images.")

        # prompt user for new focus
        print("\nPlease enter the coordinates or object you would like to focus on.")
        newFocus = input("(x,y with no spaces or parentheses for coordinates): ")

        # if switching to original
        if newFocus == "":
            
            # if already on original
            if cropFocus == "":
                print("\nThe original series is already set as the focus.")

            # switch to original if not
            else: 
                print("\nWould you like to switch to the original series?")
                input("Press enter to continue or Ctrl+c to exit.")
                print("\nSwitching to original series...")
                switchToOriginal(seriesName, cropFocus)
                print("Successfully set the original series as the focus.")

        # if switching to crop
        else:

            # if already on desired crop
            if cropFocus == newFocus:
                print("\n" + newFocus + " is already set as the focus.")

            # if switching to an existing crop
            elif os.path.isdir(seriesName + "_" + newFocus):

                # switch to the original crop if not already on
                if cropFocus != "":
                    print("\nSwitching to original crop focus to prepare...")
                    switchToOriginal(seriesName, cropFocus)
                    print("Successfully set the original series as the focus.")
                
                input("\nPress enter to continue and switch cropping focus to " + newFocus)
                print("\nSwitching to " + newFocus + "...")
                switchToCrop(seriesName, newFocus)
                print("Successfully set " + newFocus + " as the focus.")

            # if crop does not exist, make the guided crop
            else:
                print("\nThis crop does not exist.")
                input("Press enter to create a new crop for this object (press Ctrl+c to exit).")
                
                obj = newFocus # set obj variable as newFocus variable

                # switch to the original crop focus if not on already
                if cropFocus != "":
                    print("\nSwitching to original focus...")
                    switchToOriginal(seriesName, cropFocus)
                    print("Switched to original focus.")
                
                print("\nLocating the object...")

                # create a dictionary: key = section number, value = list of bounds
                bounds_dict = {}
                for sectionNum in sectionNums:
                    bounds_dict[sectionNum] = findBounds(seriesName + "." + str(sectionNum), obj)
                bounds_dict = fillInBounds(bounds_dict)

                # check to see if the object was found, raise exception if not
                noTraceFound = True
                for bounds in bounds_dict:
                    if bounds_dict[bounds] != None:
                        noTraceFound = False
                if noTraceFound:
                    raise Exception("This trace does not exist in this series.")

                print("Completed successfully!")

                # get the original series images to make the guided crop
                input("\nPress enter to select the original series images.")

                # create tkinter object but don't display extra window
                root = Tk()
                root.attributes("-topmost", True)
                root.withdraw()

                # open file explorer for user to select the image files
                imageFiles = list(askopenfilenames(title="Select Image Files",
                                           filetypes=(("Image Files", "*.tif"),
                                                      ("All Files","*.*"))))

                # stop program if user does not select images
                if len(imageFiles) == 0:
                    raise Exception("No pictures were selected.")

                
                # ask the user for the cropping rad
                rad = floatInput("\nWhat is the cropping radius in microns?: ")
                
                # create the folder for the cropped images
                newLocation = seriesName + "_" + obj
                os.mkdir(newLocation)

                # get section info for every section
                sectionInfo = {}
                for sectionNum in sectionNums:
                    sectionInfo[sectionNum] = getSectionInfo(seriesName + "." + str(sectionNum))

                # create new trace files with shift domain origins
                print("\nCreating new domain origins file...")
                newTransformationsFile = open(newLocation + "/LOCAL_TRANSFORMATIONS.txt", "w")

                # shift the domain origins to bottom left corner of planned crop
                for sectionNum in sectionNums:

                    # fix the coordinates to the picture
                    inv_orig_trans = np.linalg.inv(coefToMatrix(sectionInfo[sectionNum][0], sectionInfo[sectionNum][1])) # get the inverse section transformation
                    min_coords = np.matmul(inv_orig_trans, [[bounds_dict[sectionNum][0]],[bounds_dict[sectionNum][2]],[1]]) # transform the bottom left corner coordinates

                    # translate coordinates to pixels
                    pixPerMic = 1.0 / sectionInfo[sectionNum][2] # get image magnification
                    xshift_pix = int((min_coords[0][0] - rad) * pixPerMic)
                    if xshift_pix < 0:
                        xshift_pix = 0
                    yshift_pix = int((min_coords[1][0] - rad) * pixPerMic)
                    if yshift_pix < 0:
                        yshift_pix = 0

                    # write the shifted origin to the transformations file
                    newTransformationsFile.write("Section " + str(sectionNum) + "\n" +
                                                 "xshift: " + str(xshift_pix) + "\n" +
                                                 "yshift: " + str(yshift_pix) + "\n" +
                                                 "Dtrans: 1 0 0 0 1 0\n")

                newTransformationsFile.close()

                print("LOCAL_TRANSFORMATIONS.txt has been stored.")
                print("Do NOT delete this file.")

                print("\nCropping images around bounds...")

                # crop each image
                for sectionNum in sectionNums:   
                        
                    fileName = imageFiles[sectionNum]

                    print("\nWorking on " + fileName + "...")
                    
                    # open original image
                    img = PILImage.open(fileName)

                    # get image dimensions
                    img_length, img_height = img.size
                    
                    # get magnification
                    pixPerMic = 1.0 / sectionInfo[sectionNum][2]
                    
                    # get the bounds coordinates in pixels
                    inv_orig_trans = np.linalg.inv(coefToMatrix(sectionInfo[sectionNum][0], sectionInfo[sectionNum][1]))
                    min_coords = np.matmul(inv_orig_trans, [[bounds_dict[sectionNum][0]],[bounds_dict[sectionNum][2]],[1]])
                    max_coords = np.matmul(inv_orig_trans, [[bounds_dict[sectionNum][1]],[bounds_dict[sectionNum][3]],[1]])

                    # get the pixel coordinates for each corner of the crop
                    left = int((min_coords[0][0] - rad) * pixPerMic)
                    bottom = img_height - int((min_coords[1][0] - rad) * pixPerMic)
                    right = int((max_coords[0][0] + rad) * pixPerMic)
                    top = img_height - int((max_coords[1][0] + rad) * pixPerMic)
                    
                    # if crop exceeds image boundary, cut it off
                    if left < 0: left = 0
                    if right >= img_length: right = img_length-1
                    if top < 0: top = 0
                    if bottom >= img_height: bottom = img_height-1

                    # crop the photo
                    cropped = img.crop((left, top, right, bottom))
                    cropped.save(newLocation + "/" + seriesName + "." + str(sectionNum) + ".tif")
                    
                    print("Saved!")

                print("\nCropping has run successfully!")

                print("\nSwitching to new crop...")
                switchToCrop(seriesName, obj)

                print("Successfully set " + obj + " as the focus.")


    # cropping a new set of images if there is no detected series file
    else:
        print("\nThere does not appear to be an existing series.")
        seriesName = input("\nPlease enter the desired name for the series: ")
        input("\nPress enter to select the pictures you would like to crop.")

        # create tkinter object but don't display extra window
        root = Tk()
        root.attributes("-topmost", True)
        root.withdraw()

        # open file explorer for user to select images
        imageFiles = list(askopenfilenames(title="Select Image Files",
                                   filetypes=(("Image Files", "*.tif"),
                                              ("All Files","*.*"))))

        # stop program if user does not select images
        if len(imageFiles) == 0:
                    raise Exception("No pictures were selected.")

        # get grid information
        xchunks = intInput("\nHow many horizontal chunks would you like to have?: ")
        ychunks = intInput("How many vertical chunks would you like to have?: ")
        overlap = floatInput("How many microns of overlap should there be between chunks?: ")
        
        # get series information
        micPerPix = floatInput("\nHow many microns per pixel are there for this series?: ")
        sectionThickness = floatInput("What would you like to set as the section thickness? (in microns): ")

        # check if there is an existing transformation file
        isTrans = ynInput("\nIs there an existing transformation file for this series? (y/n): ")

        # get the transformation file if needed
        if isTrans:
            input("Press enter to select the file containing the transformations.")
            baseTransformations = askopenfilename(title="Select Transformation File",
                                   filetypes=(("Data File", "*.dat"),
                                              ("All Files","*.*")))

            # section 0 is often the grid and does not get aligned
            trans_offset = intInput("What section does the transformation start on?\n" +
                                    "(this program starts on section 0): ")

        # store domain transformation for each of the sections and store them in a text file
        origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")

        # if the series does have an existing transformation, apply it
        if isTrans:
            print("\nIdentifying and storing original transformations...")
            baseTransFile = open(baseTransformations, "r")

            # iterate through each line (or section)
            for line in baseTransFile.readlines():

                # get info from line
                splitLine = line.split()
                sectionNum = int(splitLine[0]) + trans_offset
                matrixLine = [float(num) for num in splitLine[1:7]]
                transMatrix = [[matrixLine[0],matrixLine[1],matrixLine[2]],
                               [matrixLine[3],matrixLine[4],matrixLine[5]],
                               [0,0,1]]

                # convert the translation components so that fit microns
                transMatrix[0][2] *= micPerPix
                transMatrix[1][2] *= micPerPix
                itransMatrix = np.linalg.inv(transMatrix) # get the inverse

                # write the transformation data to the original transformations file
                origTransFile.write("Section " + str(sectionNum) + "\n" +
                                    "xcoef: " + str(itransMatrix[0][2]) + " " + str(itransMatrix[0][0]) +
                                    " " + str(itransMatrix[0][1]) + " 0 0 0\n" +
                                    "xcoef: " + str(itransMatrix[1][2]) + " " + str(itransMatrix[1][0]) +
                                    " " + str(itransMatrix[1][1]) + " 0 0 0\n")
            
        # if the series does not have an existing transformation file, then set all transformations to identity
        else:
            origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")
            for i in range(len(imageFiles)):
                origTransFile.write("Section " + str(i) + "\n" +
                                          "xcoef: 0 1 0 0 0 0\n" +
                                          "ycoef: 0 0 1 0 0 0\n")        

        origTransFile.close()

        print("ORIGINAL_TRANSFORMATIONS.txt has been stored.")
        print("Do NOT delete this file.")

        # create each folder
        print("\nCreating folders...")
        for x in range(xchunks):
            for y in range(ychunks):
                os.mkdir(seriesName + "_" + str(x) + "," + str(y))

        # store new domain origins
        newDomainOrigins = []

        # store max image length and height
        img_length_max = 0
        img_height_max = 0

        # start iterating through each of the images
        for i in range(len(imageFiles)):

            print("\nWorking on " + imageFiles[i][imageFiles[i].rfind("/")+1:] + "...")

            # open image and get dimensions
            img = PILImage.open(imageFiles[i])
            img_length, img_height = img.size
            if img_length > img_length_max:
                img_length_max = img_length
            if img_height > img_height_max:
                img_height_max = img_height
            
            # iterate through each chunk and calculate the coords for each of the corners
            for x in range(xchunks):
                newDomainOrigins.append([])
                for y in range(ychunks):
                    
                    left = int((img_length-1) * x / xchunks - overlap/2 / micPerPix)
                    if left < 0:
                        left = 0
                    right = int((img_length-1) * (x+1) / xchunks + overlap/2 / micPerPix)
                    if right >= img_length:
                        right = img_length - 1
                    
                    top = int((img_height-1) * (ychunks - y-1) / ychunks - overlap/2 / micPerPix)
                    if top < 0:
                          top = 0 
                    bottom = int((img_height-1) * (ychunks - y) / ychunks + overlap/2 / micPerPix)
                    if bottom >= img_height:
                        bottom = img_height - 1

                    # crop the photo
                    cropped = img.crop((left, top, right, bottom))
                    
                    newDomainOrigins[x].append((left,
                                                int(img_height-1 - bottom)))

                    # save as uncompressed TIF
                    cropped.save(seriesName + "_" + str(x) + "," + str(y) + "/" +
                             seriesName + "." + str(i) + ".tif")

            print("Completed!")

        print("\nStoring new transformation data...")

        # iterate through each of the chunks to create the local transformations file
        for x in range(xchunks):
            for y in range(ychunks):
                newTransformationsFile = open(seriesName + "_" + str(x) + "," + str(y) +
                                             "/LOCAL_TRANSFORMATIONS.txt", "w")
                for i in range(len(imageFiles)):
                    
                    # shift the domain origins to bottom left corner of planned crop
                    xshift_pix = newDomainOrigins[x][y][0]
                    yshift_pix = newDomainOrigins[x][y][1]
                    newTransformationsFile.write("Section " + str(i) + "\n" +
                                                 "xshift: " + str(xshift_pix) + "\n" +
                                                 "yshift: " + str(yshift_pix) + "\n" +
                                                 "Dtrans: 1 0 0 0 1 0\n")
                newTransformationsFile.close()

        print("LOCAL_TRANSFORMATIONS.txt has been stored in each folder.")
        print("Do NOT delete this file.")

        print("\nCreating new section and series files...")

        # store a blank section file in the program
        # could be stored in txt file but having everything in one file keeps it simple for user
        blankSectionFile = """<?xml version="1.0"?>
    <!DOCTYPE Section SYSTEM "section.dtd">
    <Section index="[SECTION_INDEX]" thickness="[SECTION_THICKNESS]" alignLocked="false">
    <Transform dim="[TRANSFORM_DIM]"
     xcoef="[XCOEF]"
     ycoef="[YCOEF]">
    <Image mag="[IMAGE_MAG]" contrast="1" brightness="0" red="true" green="true" blue="true"
     src="[IMAGE_SOURCE]" />
    <Contour name="domain1" hidden="false" closed="true" simplified="false" border="1 0 1" fill="1 0 1" mode="11"
     points="0 0,
            [IMAGE_LENGTH] 0,
            [IMAGE_LENGTH] [IMAGE_HEIGHT],
            0 [IMAGE_HEIGHT],
            "/>
    </Transform>
    </Section>"""

        # replace the unknowns in the section file with known info
        blankSectionFile = blankSectionFile.replace("[SECTION_THICKNESS]", str(sectionThickness))
        blankSectionFile = blankSectionFile.replace("[TRANSFORM_DIM]", "3")
        blankSectionFile = blankSectionFile.replace("[IMAGE_MAG]", str(micPerPix))
        blankSectionFile = blankSectionFile.replace("[IMAGE_LENGTH]", str(int(img_length_max)))
        blankSectionFile = blankSectionFile.replace("[IMAGE_HEIGHT]", str(int(img_height_max)))

        origTrans = open("ORIGINAL_TRANSFORMATIONS.txt", "r")

        # iterate through each section and create the section file
        for i in range(len(imageFiles)):
            newSectionFile = open(seriesName + "." + str(i), "w")

            # retrieve original transformations
            origTrans.readline()
            xcoef_data = origTrans.readline()
            xcoef_str = xcoef_data[xcoef_data.find(":")+1 : xcoef_data.find("\n")]
            ycoef_data = origTrans.readline()
            ycoef_str = ycoef_data[ycoef_data.find(":")+1 : ycoef_data.find("\n")]

            # replace section-specific unknowns with known info
            sectionFileText = blankSectionFile.replace("[SECTION_INDEX]", str(i))
            sectionFileText = sectionFileText.replace("[IMAGE_SOURCE]", seriesName + "." + str(i) + ".tif")
            sectionFileText = sectionFileText.replace("[XCOEF]", xcoef_str)
            sectionFileText = sectionFileText.replace("[YCOEF]", ycoef_str)

            newSectionFile.write(sectionFileText)
            newSectionFile.close()

        # create the series file
        blankSeriesFile = """<?xml version="1.0"?>
    <!DOCTYPE Series SYSTEM "series.dtd">
    <Series index="0" viewport="0 0 0.00254"
            units="microns"
            autoSaveSeries="true"
            autoSaveSection="true"
            warnSaveSection="true"
            beepDeleting="true"
            beepPaging="true"
            hideTraces="false"
            unhideTraces="false"
            hideDomains="false"
            unhideDomains="false"
            useAbsolutePaths="false"
            defaultThickness="0.05"
            zMidSection="false"
            thumbWidth="128"
            thumbHeight="96"
            fitThumbSections="false"
            firstThumbSection="1"
            lastThumbSection="2147483647"
            skipSections="1"
            displayThumbContours="true"
            useFlipbookStyle="false"
            flipRate="5"
            useProxies="true"
            widthUseProxies="2048"
            heightUseProxies="1536"
            scaleProxies="0.25"
            significantDigits="6"
            defaultBorder="1.000 0.000 1.000"
            defaultFill="1.000 0.000 1.000"
            defaultMode="9"
            defaultName="domain$+"
            defaultComment=""
            listSectionThickness="true"
            listDomainSource="true"
            listDomainPixelsize="true"
            listDomainLength="false"
            listDomainArea="false"
            listDomainMidpoint="false"
            listTraceComment="true"
            listTraceLength="false"
            listTraceArea="true"
            listTraceCentroid="false"
            listTraceExtent="false"
            listTraceZ="false"
            listTraceThickness="false"
            listObjectRange="true"
            listObjectCount="true"
            listObjectSurfarea="false"
            listObjectFlatarea="false"
            listObjectVolume="false"
            listZTraceNote="true"
            listZTraceRange="true"
            listZTraceLength="true"
            borderColors="0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    "
            fillColors="0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    0.000 0.000 0.000,
                    "
            offset3D="0 0 0"
            type3Dobject="0"
            first3Dsection="1"
            last3Dsection="2147483647"
            max3Dconnection="-1"
            upper3Dfaces="true"
            lower3Dfaces="true"
            faceNormals="false"
            vertexNormals="true"
            facets3D="8"
            dim3D="-1 -1 -1"
            gridType="0"
            gridSize="1 1"
            gridDistance="1 1"
            gridNumber="1 1"
            hueStopWhen="3"
            hueStopValue="50"
            satStopWhen="3"
            satStopValue="50"
            brightStopWhen="0"
            brightStopValue="100"
            tracesStopWhen="false"
            areaStopPercent="999"
            areaStopSize="0"
            ContourMaskWidth="0"
            smoothingLength="7"
            mvmtIncrement="0.022 1 1 1.01 1.01 0.02 0.02 0.001 0.001"
            ctrlIncrement="0.0044 0.01 0.01 1.002 1.002 0.004 0.004 0.0002 0.0002"
            shiftIncrement="0.11 100 100 1.05 1.05 0.1 0.1 0.005 0.005"
            >
    <Contour name="a$+" closed="true" border="1.000 0.500 0.000" fill="1.000 0.500 0.000" mode="13"
     points="-3 1,
            -3 -1,
            -1 -3,
            1 -3,
            3 -1,
            3 1,
            1 3,
            -1 3,
            "/>
    <Contour name="b$+" closed="true" border="0.500 0.000 1.000" fill="0.500 0.000 1.000" mode="13"
     points="-2 1,
            -5 0,
            -2 -1,
            -4 -4,
            -1 -2,
            0 -5,
            1 -2,
            4 -4,
            2 -1,
            5 0,
            2 1,
            4 4,
            1 2,
            0 5,
            -1 2,
            -4 4,
            "/>
    <Contour name="pink$+" closed="true" border="1.000 0.000 0.500" fill="1.000 0.000 0.500" mode="-13"
     points="-6 -6,
            6 -6,
            0 5,
            "/>
    <Contour name="X$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="-13"
     points="-7 7,
            -2 0,
            -7 -7,
            -4 -7,
            0 -1,
            4 -7,
            7 -7,
            2 0,
            7 7,
            4 7,
            0 1,
            -4 7,
            "/>
    <Contour name="yellow$+" closed="true" border="1.000 1.000 0.000" fill="1.000 1.000 0.000" mode="-13"
     points="8 8,
            8 -8,
            -8 -8,
            -8 6,
            -10 8,
            -10 -10,
            10 -10,
            10 10,
            -10 10,
            -8 8,
            "/>
    <Contour name="blue$+" closed="true" border="0.000 0.000 1.000" fill="0.000 0.000 1.000" mode="9"
     points="0 7,
            -7 0,
            0 -7,
            7 0,
            "/>
    <Contour name="magenta$+" closed="true" border="1.000 0.000 1.000" fill="1.000 0.000 1.000" mode="9"
     points="-6 2,
            -6 -2,
            -2 -6,
            2 -6,
            6 -2,
            6 2,
            2 6,
            -2 6,
            "/>
    <Contour name="red$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="9"
     points="6 -6,
            0 -6,
            0 -3,
            3 0,
            12 3,
            6 6,
            3 12,
            -3 6,
            -6 0,
            -6 -6,
            -12 -6,
            -3 -12,
            "/>
    <Contour name="green$+" closed="true" border="0.000 1.000 0.000" fill="0.000 1.000 0.000" mode="9"
     points="-12 4,
            -12 -4,
            -4 -4,
            -4 -12,
            4 -12,
            4 -4,
            12 -4,
            12 4,
            4 4,
            4 12,
            -4 12,
            -4 4,
            "/>
    <Contour name="cyan$+" closed="true" border="0.000 1.000 1.000" fill="0.000 1.000 1.000" mode="9"
     points="0 12,
            4 8,
            -12 -8,
            -8 -12,
            8 4,
            12 0,
            12 12,
            "/>
    <Contour name="a$+" closed="true" border="1.000 0.500 0.000" fill="1.000 0.500 0.000" mode="13"
     points="-3 1,
            -3 -1,
            -1 -3,
            1 -3,
            3 -1,
            3 1,
            1 3,
            -1 3,
            "/>
    <Contour name="b$+" closed="true" border="0.500 0.000 1.000" fill="0.500 0.000 1.000" mode="13"
     points="-2 1,
            -5 0,
            -2 -1,
            -4 -4,
            -1 -2,
            0 -5,
            1 -2,
            4 -4,
            2 -1,
            5 0,
            2 1,
            4 4,
            1 2,
            0 5,
            -1 2,
            -4 4,
            "/>
    <Contour name="pink$+" closed="true" border="1.000 0.000 0.500" fill="1.000 0.000 0.500" mode="-13"
     points="-6 -6,
            6 -6,
            0 5,
            "/>
    <Contour name="X$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="-13"
     points="-7 7,
            -2 0,
            -7 -7,
            -4 -7,
            0 -1,
            4 -7,
            7 -7,
            2 0,
            7 7,
            4 7,
            0 1,
            -4 7,
            "/>
    <Contour name="yellow$+" closed="true" border="1.000 1.000 0.000" fill="1.000 1.000 0.000" mode="-13"
     points="8 8,
            8 -8,
            -8 -8,
            -8 6,
            -10 8,
            -10 -10,
            10 -10,
            10 10,
            -10 10,
            -8 8,
            "/>
    <Contour name="blue$+" closed="true" border="0.000 0.000 1.000" fill="0.000 0.000 1.000" mode="9"
     points="0 7,
            -7 0,
            0 -7,
            7 0,
            "/>
    <Contour name="magenta$+" closed="true" border="1.000 0.000 1.000" fill="1.000 0.000 1.000" mode="9"
     points="-6 2,
            -6 -2,
            -2 -6,
            2 -6,
            6 -2,
            6 2,
            2 6,
            -2 6,
            "/>
    <Contour name="red$+" closed="true" border="1.000 0.000 0.000" fill="1.000 0.000 0.000" mode="9"
     points="6 -6,
            0 -6,
            0 -3,
            3 0,
            12 3,
            6 6,
            3 12,
            -3 6,
            -6 0,
            -6 -6,
            -12 -6,
            -3 -12,
            "/>
    <Contour name="green$+" closed="true" border="0.000 1.000 0.000" fill="0.000 1.000 0.000" mode="9"
     points="-12 4,
            -12 -4,
            -4 -4,
            -4 -12,
            4 -12,
            4 -4,
            12 -4,
            12 4,
            4 4,
            4 12,
            -4 12,
            -4 4,
            "/>
    <Contour name="cyan$+" closed="true" border="0.000 1.000 1.000" fill="0.000 1.000 1.000" mode="9"
     points="0 12,
            4 8,
            -12 -8,
            -8 -12,
            8 4,
            12 0,
            12 12,
            "/>
    </Series>"""

        newSeriesFile = open(seriesName + ".ser", "w")
        newSeriesFile.write(blankSeriesFile)
        newSeriesFile.close()
        print("Completed!")

        print("\nSwitching focus to (0,0)...")
        switchToCrop(seriesName, "0,0")
        print("Completed!")

except Exception as e:
    print(e)


input("\nPress enter to exit.")
