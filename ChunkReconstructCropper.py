from PIL import Image as PILImage
PILImage.MAX_IMAGE_PIXELS = None
import os
import numpy as np
from tkinter import *
from tkinter.filedialog import askopenfilename, askopenfilenames


def findCenter(fileName, obj):
    """Finds the center of a specified object on a single trace file."""
    
    # open trace file, read lines, and close
    sectionFile = open(fileName, 'r')
    lines = sectionFile.readlines()    
    sectionFile.close()
    
    # set up sums for averages
    xsum = 0
    ysum = 0
    total = 0
    
    # recording: set to True whenever the points in the file are being recorded
    recording = False
    
    for lineIndex in range(len(lines)):
        
        # grab line
        line = lines[lineIndex]
        
        # if data points are being recorded from the trace file...
        if recording:
            
            # keep track of total points
            total += 1
            
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
                                       [1]])
                trans_mat = np.linalg.inv(np.array([[xcoef[1],xcoef[2],xcoef[0]],
                                      [ycoef[1],ycoef[2],ycoef[0]],
                                      [0,0,1]]))
                trans_coords = np.matmul(trans_mat, coords_mat)
                xsum += trans_coords[0][0]
                ysum += trans_coords[1][0]
            
            # stop recording otherwise
            else:
                total -= 1
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

                # raise exception if transformation dimension is higher than 3
                ##dim = int(lines[xcoefIndex-1].split('"')[1])
                ##if dim > 3:
                ##    raise Exception("This program cannot work with transformation dimensions higher than three.")
                
                # set the xcoef and ycoef
                xcoef = [float(x) for x in lines[xcoefIndex].split()[1:4]]
                ycoef = [float(y) for y in lines[xcoefIndex+1].split()[1:4]]
    
    # if the trace is not found in the section
    if total == 0:
        return None, None
    
    # return averages
    return xsum/total, ysum/total


def fillInCenters(centers):
    """Fills in center data where object doesn't exist with center data from previous sections."""
    
    # if the first section(s) do not have the object, then fill it in with first object instance
    firstInstanceFound = False
    prevCenter = (None, None)
    for center in centers:
        if centers[center] != (None, None) and not firstInstanceFound:
            prevCenter = centers[center]
            firstInstanceFound = True
    
    # set any center points that are (None, None) to the previous center
    for center in centers:
        if centers[center] == (None, None):
            centers[center] = prevCenter
        prevCenter = centers[center]
    
    return centers


def getSectionInfo(fileName):
    """Gets the domain origin data from a single trace file."""
    
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
    
    # raise exception if transformation dimension is higher than 3
    ##dim = int(lines[domainIndex-5].split('"')[1])
    ##if dim > 3:
    ##    raise Exception("This program cannot work with transformation dimensions higher than three.")

    # grab xcoef transformation
    xcoef = [float(x) for x in lines[domainIndex-4].replace('"',"").split()[1:4]]

    # grab ycoef transformation
    ycoef = [float(y) for y in lines[domainIndex-3].replace('">',"").split()[1:4]]

    # get magnification and image source
    mag = float(lines[domainIndex-2].split('"')[1])
    src = lines[domainIndex-1].split('"')[1]    

    return xcoef, ycoef, mag, src

    
def getSeriesInfo(fileName):
    """Return the series name and section number"""

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
        
    sectionNums.sort()

    return seriesName, sectionNums


def switchToOriginal(seriesName, objName):
    """Switch focus to a cropped series from the original"""

    # check for new transformations
    iDtransList = checkForRealignment(seriesName, objName)

    # open the transformation files
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    newLocalTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "w")

    # store the new transformations and grab shifts for each section
    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1])
        elif "xshift" in line:
            xshift_pix = int(line.split()[1])
        elif "yshift" in line:
            yshift_pix = int(line.split()[1])
            
        elif "Dtrans" in line:
            # edit all of the traces in the section
            transformAllTraces(seriesName + "." + str(sectionNum),
                               iDtransList[sectionNum],
                               -xshift_pix, -yshift_pix, "")
            
            # store the transformation matrix going from original to cropped
            Dtrans = np.linalg.inv(iDtransList[sectionNum])
            line = "Dtrans: "
            line += str(Dtrans[0,0]) + " "
            line += str(Dtrans[0,1]) + " "
            line += str(Dtrans[0,2]) + " "
            line += str(Dtrans[1,0]) + " "
            line += str(Dtrans[1,1]) + " "
            line += str(Dtrans[1,2]) + "\n"
                
        newLocalTrans.write(line)

    newLocalTrans.close()
            

def switchToCrop(seriesName, objName):
    """Switch focus to an original series from a cropped one"""
    
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

    # grab transformation data from each of the files
    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1])
        elif "xshift" in line:
            xshift_pix = int(line.split()[1])
        elif "yshift" in line:
            yshift_pix = int(line.split()[1])
        elif "Dtrans" in line:
            Dtrans = [float(z) for z in line.split()[1:7]]
            DtransMatrix = [[Dtrans[0],Dtrans[1],Dtrans[2]],
                                 [Dtrans[3],Dtrans[4],Dtrans[5]],
                                 [0,0,1]]

            # transform all the traces by the Dtrans matrix
            transformAllTraces(seriesName + "." + str(sectionNum), DtransMatrix, xshift_pix, yshift_pix, objName)
        
    
def checkForRealignment(seriesName, objName):
    """Check for differences in base alignment between cropped and original series"""

    # open the two transformation files
    origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "r")
    localTransFile = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")

    # read through each of the files and gather data
    iDtransList = {}
    for localLine in localTransFile.readlines():
        if "Section" in localLine:
            origTransFile.readline()
            sectionNum = int(localLine.split()[1])
            sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))
            local_xcoef = sectionInfo[0]
            local_ycoef = sectionInfo[1]
        elif "xshift" in localLine:
            origLine = origTransFile.readline()
            orig_xcoef = [float(x) for x in origLine.split()[1:4]]
            xshift = int(localLine.split()[1]) * sectionInfo[2]
        elif "yshift" in localLine:
            origLine = origTransFile.readline()
            orig_ycoef = [float(y) for y in origLine.split()[1:4]]
            yshift = int(localLine.split()[1]) * sectionInfo[2]

        # check for realignment using the two matrices
        elif "Dtrans" in localLine:
            # set up the two matrices
            local_matrix = coefToMatrix(local_xcoef, local_ycoef)
            orig_matrix = coefToMatrix(orig_xcoef, orig_ycoef)
            transformedShiftCoords = np.matmul(local_matrix[:2,:2], [[xshift],[yshift]])
            local_matrix[0][2] -= transformedShiftCoords[0][0]
            local_matrix[1][2] -= transformedShiftCoords[1][0]
            # get the "difference" between the two matrices and store the result
            z_matrix = np.matmul(orig_matrix, np.linalg.inv(local_matrix))
            iDtransList[sectionNum] = z_matrix
        
    origTransFile.close()
    localTransFile.close()

    return iDtransList


def transformAllTraces(fileName, transformation, xshift_pix, yshift_pix, objName):
    """Multiply all of the traces on a section by a transformation matrix while also changing the image domain and source"""

    # get section info
    sectionInfo = getSectionInfo(fileName)
    sectionNum = int(fileName[fileName.rfind(".")+1:])
    
    # check if transformation is needed
    transformation = np.array(transformation)
    noTrans = np.array([[1,0,0],[0,1,0],[0,0,1]])
    needsTransformation = not (np.round(transformation, decimals = 8) == noTrans).all()

    # make the domain transformation matrix
    existingDomainTrans = coefToMatrix(sectionInfo[0],sectionInfo[1])
    transformedShiftCoords = np.matmul(existingDomainTrans[:2,:2],
                                       [[xshift_pix*sectionInfo[2]],[yshift_pix*sectionInfo[2]]])
    transformedShiftCoords = np.matmul(transformation[:2,:2], transformedShiftCoords)
    domainTransformation = transformation.copy()
    domainTransformation[0][2] += transformedShiftCoords[0][0]
    domainTransformation[1][2] += transformedShiftCoords[1][0]
    
    # open the section file    
    sectionFile = open(fileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()

    # check for domain in the text to find domain origin index
    domainIndex = 0
    line = lines[domainIndex]
    while not '"domain1"' in line:
        domainIndex += 1
        line = lines[domainIndex]

    newSectionFile = open(fileName, "w")

    # read through the file
    for i in range(len(lines)):
        line = lines[i]

        # make sure the dimension is set to three
        if '<Transform dim="0"' in line:
            line = line.replace("0", "3")
        
        elif i == domainIndex - 4:
            # gather the matrices and multiply them by the transformation matrix
            xcoef = [float(x) for x in line.split()[1:4]]
            ycoef = [float(y) for y in lines[i+1].split()[1:4]]
            newMatrix = np.linalg.inv(np.matmul(domainTransformation, coefToMatrix(xcoef, ycoef)))

            # write the new matrices to the file
            
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
        
        elif i == domainIndex - 3:
            line = ycoef_line

        # create a new image directory
        elif i == domainIndex - 1:
            imageFile = line.split('"')[1]
            if "/" in imageFile:
                imageFile = imageFile[imageFile.find("/")+1:]
            if not objName == "":
                imageFile = seriesName + "_" + objName + "/" + imageFile
                
            line = ' src="' + imageFile + '" />\n'
        
        elif needsTransformation and "xcoef" in line:
            # gather the matrices and multiply them by the transformation matrix
            xcoef = [float(x) for x in line.split()[1:4]]
            ycoef = [float(y) for y in lines[i+1].split()[1:4]]
            newMatrix = np.linalg.inv(np.matmul(transformation, coefToMatrix(xcoef, ycoef)))

            # write the new matrices to the file
            
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
        
        elif needsTransformation and "ycoef" in line:
            line = ycoef_line

        newSectionFile.write(line)

    newSectionFile.close()


def coefToMatrix(xcoef, ycoef):
    """Turn a set of x and y coef into a transformation matrix"""
    
    return np.linalg.inv(np.array([[xcoef[1], xcoef[2], xcoef[0]],
                       [ycoef[1], ycoef[2], ycoef[0]],
                       [0, 0, 1]]))


def getCropFocus(sectionFileName):
    """Find the current crop focus"""

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
        cropFocus = folder[folder.rfind("_")+1:]
    else:
        cropFocus = ""

    return cropFocus


def saveOriginalTransformations(seriesName, sectionNums):
    transformationsFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")
    for sectionNum in sectionNums:
        sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))
        xcoef_str = ""
        for x in sectionInfo[0]:
            xcoef_str += str(x) + " "
        ycoef_str = ""
        for y in sectionInfo[1]:
            ycoef_str += str(y) + " "
        transformationsFile.write("Section " + str(sectionNum) + "\n"
                                  "xcoef: " + xcoef_str + "\n" +
                                  "ycoef: " + ycoef_str + "\n")
    transformationsFile.close()


def intInput(inputStr):
    isInt = False
    while not isInt:
        try:
            num = int(input(inputStr))
            isInt = True
        except ValueError:
            print("Please enter a valid integer.")
    return num

def floatInput(inputStr):
    isFloat = False
    while not isFloat:
        try:
            num = float(input(inputStr))
            isFloat = True
        except ValueError:
            print("Please enter a valid number.")
    return num

def ynInput(inputStr):
    response = input(inputStr)
    while response != "y" and response != "n":
        print("Please enter y or n.")
        response = input(inputStr)
    if response == "y":
        return True
    return False



# BEGINNING OF MAIN: gather inputs
##try:

# locate the series file and gather pertinent info
print("Locating series file...")
fileName = ""
for file in os.listdir("."):
    if file.endswith(".ser"):
        fileName = str(file)

# switch crops if there is an existing series file
if fileName:
    seriesName, sectionNums = getSeriesInfo(fileName)

    # find the current crop focus
    cropFocus = getCropFocus(seriesName + "." + str(sectionNums[0]))
    if cropFocus:
        print("This series is currently focused on: " + cropFocus)
    else:
        print("This series is currently set to the original set of images.")

    # gather inputs
    print("\nPlease enter the coordinates or object you would like to focus on.")
    newFocus = input("(x,y with no spaces or parentheses): ")

    # if switching to original
    if newFocus == "":
        if cropFocus == "":
            print("\nThe original series is already set as the focus.")
        else:
            print("\nWould you like to switch to the original series?")
            input("Press enter to continue or Ctrl+c to exit.")
            print("\nSwitching to original series...")
            switchToOriginal(seriesName, cropFocus)
            print("Successfully set the original series as the focus.")

    # if switching to existing crop
    else:
        if cropFocus == newFocus:
            print("\n" + newFocus + " is already set as the focus.")
        elif not os.path.isdir(seriesName + "_" + newFocus):
            print("\nThis crop does not exist.")
            input("Press enter to create a new crop for this object (press Ctrl+c to exit).")
            obj = newFocus
            print("\nLocating the object...")

            centers = {}
            for sectionNum in sectionNums:
                centers[sectionNum] = findCenter(seriesName + "." + str(sectionNum), obj)

            # check to see if the object was found, raise exception if not
            noTraceFound = True
            for center in centers:
                if centers[center] != (None,None):
                    noTraceFound = False
            if noTraceFound:
                raise Exception("This trace does not exist in this series.")

            centers = fillInCenters(centers)

            print("Completed successfully!")
            
            print("\nSwitching to original focus...")
            switchToOriginal(seriesName, cropFocus)
            print("Switched to original focus.")

            # get the original series images
            input("\nPress enter to select the original series images.")

            root = Tk()
            root.attributes("-topmost", True)
            root.withdraw()
            
            imageFiles = list(askopenfilenames(title="Select Image Files",
                                       filetypes=(("Image Files", "*.tif"),
                                                  ("All Files","*.*"))))
            if len(imageFiles) == 0:
                raise Exception("No pictures were selected.")

            
            # ask the user for the cropping rad
            rad = floatInput("\nWhat is the cropping radius in microns?: ")

            newLocation = seriesName + "_" + obj
            os.mkdir(newLocation)
            
            sectionInfo = {}
            for sectionNum in sectionNums:
                sectionInfo[sectionNum] = getSectionInfo(seriesName + "." + str(sectionNum))

            # Create new trace files with shift domain origins

            print("\nCreating new domain origins file...")

            newTransformationsFile = open(newLocation + "/LOCAL_TRANSFORMATIONS.txt", "w")

            for sectionNum in sectionNums:
                
                # shift the domain origins to bottom left corner of planned crop
                orig_trans = coefToMatrix(sectionInfo[sectionNum][0], sectionInfo[sectionNum][1])
                untransformedCenter = np.matmul(np.linalg.inv(orig_trans),
                                                [[centers[sectionNum][0]],[centers[sectionNum][1]],[1]])
                pixPerMic = 1.0 / sectionInfo[sectionNum][2]
                xshift_pix = int((untransformedCenter[0][0] - rad) * pixPerMic)
                if xshift_pix < 0:
                    xshift_pix = 0
                yshift_pix = int((untransformedCenter[1][0] - rad) * pixPerMic)
                if yshift_pix < 0:
                    yshift_pix = 0
                newTransformationsFile.write("Section " + str(sectionNum) + "\n" +
                                             "xshift: " + str(xshift_pix) + "\n" +
                                             "yshift: " + str(yshift_pix) + "\n" +
                                             "Dtrans: 1 0 0 0 1 0\n")

            newTransformationsFile.close()

            print("LOCAL_TRANSFORMATIONS.txt has been stored.")
            print("Do NOT delete this file.")

            # Crop each image

            print("\nCropping images around centers...")

            for sectionNum in sectionNums:   
                    
                fileName = imageFiles[sectionNum]

                print("\nWorking on " + fileName + "...")
                
                # open original image
                img = PILImage.open(fileName)

                # get image dimensions
                img_length, img_height = img.size
                
                # get magnification
                pixPerMic = 1.0 / sectionInfo[sectionNum][2]
                
                # get the cropping radius in pixels
                pixRad = rad * pixPerMic
                
                # get the center coordinates in pixels
                orig_trans = coefToMatrix(sectionInfo[sectionNum][0], sectionInfo[sectionNum][1])
                untransformedCenter = np.matmul(np.linalg.inv(orig_trans),
                                                [[centers[sectionNum][0]],[centers[sectionNum][1]],[1]])
                
                # get the pixel coordinates for each corner of the crop
                left = int((untransformedCenter[0][0] - rad) * pixPerMic)
                bottom = img_height - int((untransformedCenter[1][0] - rad) * pixPerMic)
                right = int((untransformedCenter[0][0] + rad) * pixPerMic)
                top = img_height - int((untransformedCenter[1][0] + rad) * pixPerMic)

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
        
        else:
            if cropFocus != "":
                # switch to the original crop if not already on
                print("\nSwitching to original crop focus to prepare...")
                switchToOriginal(seriesName, cropFocus)
                print("Successfully set the original series as the focus.")
            input("\nPress enter to continue and switch cropping focus to " + newFocus)
            print("\nSwitching to " + newFocus + "...")
            switchToCrop(seriesName, newFocus)
            print("Successfully set " + newFocus + " as the focus.")


# cropping a new set of images if there is no detected series file
else:
    print("\nThere does not appear to be an existing series.")
    seriesName = input("\nPlease enter the desired name for the series: ")
    input("\nPress enter to select the pictures you would like to crop.")

    root = Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    
    imageFiles = list(askopenfilenames(title="Select Image Files",
                               filetypes=(("Image Files", "*.tif"),
                                          ("All Files","*.*"))))
    if len(imageFiles) == 0:
                raise Exception("No pictures were selected.")
    
    xchunks = intInput("\nHow many horizontal chunks would you like to have?: ")
    ychunks = intInput("How many vertical chunks would you like to have?: ")

    micPerPix = floatInput("\nHow many microns per pixel are there for this series?: ")
    sectionThickness = floatInput("What would you like to set as the section thickness?: ")
    overlap = floatInput("How many microns of overlap should there be between chunks?: ")

    isTrans = ynInput("\nIs there an existing transformation file for this series? (y/n): ")

    if isTrans:
        input("Press enter to select the file containing the transformations.")
        baseTransformations = askopenfilename(title="Select Transformation File",
                               filetypes=(("Data File", "*.dat"),
                                          ("All Files","*.*")))

    # store domain transformation for each of the sections and store them in a text file
    origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")
    
    if isTrans:
        print("\nIdentifying and storing original transformations...")
        baseTransFile = open(baseTransformations, "r")
        for line in baseTransFile.readlines():
            splitLine = line.split()
            sectionNum = int(splitLine[0])
            matrixLine = [float(num) for num in splitLine[1:7]]
            transMatrix = [[matrixLine[0],matrixLine[1],matrixLine[2]],
                           [matrixLine[3],matrixLine[4],matrixLine[5]],
                           [0,0,1]]
            transMatrix[0][2] *= micPerPix
            transMatrix[1][2] *= micPerPix
            itransMatrix = np.linalg.inv(transMatrix)
            origTransFile.write("Section " + str(sectionNum) + "\n" +
                                "xcoef: " + str(itransMatrix[0][2]) + " " + str(itransMatrix[0][0]) +
                                " " + str(itransMatrix[0][1]) + " 0 0 0\n" +
                                "xcoef: " + str(itransMatrix[1][2]) + " " + str(itransMatrix[1][0]) +
                                " " + str(itransMatrix[1][1]) + " 0 0 0\n")
        
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

    # Create new local transformations files

    print("\nStoring new transformation data...")

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
                  

    # create blank section and series files

    print("\nCreating new section and series files...")
    
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

    blankSectionFile = blankSectionFile.replace("[SECTION_THICKNESS]", str(sectionThickness))
    blankSectionFile = blankSectionFile.replace("[TRANSFORM_DIM]", "3")

    blankSectionFile = blankSectionFile.replace("[IMAGE_MAG]", str(micPerPix))
    blankSectionFile = blankSectionFile.replace("[IMAGE_LENGTH]", str(int(img_length_max)))
    blankSectionFile = blankSectionFile.replace("[IMAGE_HEIGHT]", str(int(img_height_max)))

    
    origTrans = open("ORIGINAL_TRANSFORMATIONS.txt", "r")
    
    for i in range(len(imageFiles)):
        newSectionFile = open(seriesName + "." + str(i), "w")

        # retrieve original transformations
        origTrans.readline()
        xcoef_data = origTrans.readline()
        xcoef_str = xcoef_data[xcoef_data.find(":")+1 : xcoef_data.find("\n")]
        ycoef_data = origTrans.readline()
        ycoef_str = ycoef_data[ycoef_data.find(":")+1 : ycoef_data.find("\n")]

        sectionFileText = blankSectionFile.replace("[SECTION_INDEX]", str(i))
        sectionFileText = sectionFileText.replace("[IMAGE_SOURCE]", seriesName + "." + str(i) + ".tif")
        sectionFileText = sectionFileText.replace("[XCOEF]", xcoef_str)
        sectionFileText = sectionFileText.replace("[YCOEF]", ycoef_str)

        newSectionFile.write(sectionFileText)
        newSectionFile.close()

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
    
input("\nPress enter to exit.")
