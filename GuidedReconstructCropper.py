from PIL import Image as PILImage
PILImage.MAX_IMAGE_PIXELS = None
import os
import numpy as np


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
    
    # raise exception if transformation dimension is higher than 3
    ##dim = int(lines[domainIndex-5].split('"')[1])
    ##if dim > 3:
    ##    raise Exception("This program cannot work with transformation dimensions higher than three.")

    # grab xcoef transformation
    xcoef = [float(x) for x in lines[domainIndex-4].replace('"',"").split()[1:4]]

    # grab ycoef transformation
    ycoef = [float(y) for y in lines[domainIndex-3].replace('">',"").split()[1:4]]

    # convert to transformation matrix
    domain_trans = coefToMatrix(xcoef, ycoef)
    
    # create variables
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
                                       [1]])
                trans_mat = np.linalg.inv(np.array([[xcoef[1],xcoef[2],xcoef[0]],
                                      [ycoef[1],ycoef[2],ycoef[0]],
                                      [0,0,1]]))
                inv_domain_trans = np.linalg.inv(domain_trans)
                trans_coords = np.matmul(trans_mat, coords_mat)
                trans_coords_idomain = np.matmul(inv_domain_trans, trans_coords)

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
                else:
                    if trans_coords_idomain[0][0] < xmin_idomain:
                        xmin = trans_coords[0][0]
                        xmin_idomain = trans_coods_idomain[0][0]
                    if trans_coords_idomain[0][0] > xmax_idomain:
                        xmax = trans_coords[0][0]
                        xmax_idomain = trans_coods_idomain[0][0]
                    if trans_coords_idomain[1][0] < ymin_idomain:
                        ymin = trans_coords[1][0]
                        ymin_idomain = trans_coods_idomain[1][0]
                    if trans_coords_idomain[1][0] > ymax_idomain:
                        ymax = trans_coords[1][0]
                        ymax_idomain = trans_coods_idomain[1][0]
            
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

                # raise exception if transformation dimension is higher than 3
                ##dim = int(lines[xcoefIndex-1].split('"')[1])
                ##if dim > 3:
                ##    raise Exception("This program cannot work with transformation dimensions higher than three.")
                
                # set the xcoef and ycoef
                xcoef = [float(x) for x in lines[xcoefIndex].split()[1:4]]
                ycoef = [float(y) for y in lines[xcoefIndex+1].split()[1:4]]
    
    # if the trace is not found in the section
    if xmin == 0 and xmax == 0 and ymin == 0 and ymax == 0:
        return None
    
    # return bounds
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


def getCropFocus(sectionFileName, seriesName):
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
        cropFocus = folder[folder.find(seriesName)+len(seriesName)+1:]
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


def floatInput(inputStr):
    isFloat = False
    while not isFloat:
        try:
            num = float(input(inputStr))
            isFloat = True
        except ValueError:
            print("Please enter a valid number.")
    return num



# BEGINNING OF MAIN: gather inputs

print("Locating series file...")
# locate the series file and gather pertinent info
for file in os.listdir("."):
    if file.endswith(".ser"):
        fileName = str(file)
seriesName, sectionNums = getSeriesInfo(fileName)

# find the current crop focus
print("Finding crop focus...")
cropFocus = getCropFocus(seriesName + "." + str(sectionNums[0]), seriesName)
if cropFocus:
    print("\nThis series is currently focused on: " + cropFocus)
else:
    print("\nThis series is currently set to the original set of images.")

# gather inputs
print("\nPlease enter the name of the object you would like to focus on.")
obj = input("(enter nothing if you would like to focus on the original series): ")

# if the object is already cropped OR if the user would like to switch to the original
# (i.e. no cropping is required)
if os.path.isdir(seriesName + "_" + obj) or obj == "":
    
    # if switching to original
    if obj == "":
        if cropFocus == "":
            print("\nThe original series is already set as the focus.")
        else:
            print("\nWould you like to switch to the original series?")
            input("Press enter to continue or Ctrl+c to exit.")
            print("\nSwitching to original...")
            switchToOriginal(seriesName, cropFocus)
            print("Successfully set the original series as the focus.")

    # if switching to existing crop
    else:
        if cropFocus == obj:
            print("\n" + obj + " is already set as the focus.")
        else:
            print("\nA cropped set of images for " + obj + " exists.")
            input("Press enter to continue and switch cropping focus to " + obj + ".")
            if cropFocus != "":
                # switch to the original crop if not already on
                print("\nSwitching to original crop focus to prepare...")
                switchToOriginal(seriesName, cropFocus)
                print("Successfully set the original series as the focus.")
            
            print("\nSwitching to crop...")
            switchToCrop(seriesName, obj)
            print("Successfully set " + obj + " as the focus.")

# cropping a new set of images
else:
    print("\nThere does not appear to be an existing set of cropped pictures.")
    input("Press enter to continue and create them.")

    # switch to the original and set the crop focus as such if not already
    if os.path.isfile("ORIGINAL_TRANSFORMATIONS.txt") and cropFocus != "":
        print("\nSwitching to original crop to prepare...")
        switchToOriginal(seriesName, cropFocus)
        cropFocus = ""
        print("Successfully set the original series as the focus.")

    # Find the bounds points for the object and fill in missing bounds

    print("\nLocating the object...")

    bounds_dict = {}
    for sectionNum in sectionNums:
        bounds_dict[sectionNum] = findBounds(seriesName + "." + str(sectionNum), obj)

    # check to see if the object was found, raise exception if not
    noTraceFound = True
    for bounds in bounds_dict:
        if bounds_dict[bounds] != None:
            noTraceFound = False
    if noTraceFound:
        raise Exception("This trace does not exist in this series.")

    bounds_dict = fillInBounds(bounds_dict)

    print("Completed successfully!")

    # ask the user for the cropping rad
    rad = floatInput("\nWhat is the cropping radius around the bounds of the object? (in microns): ")

    newLocation = seriesName + "_" + obj
    os.mkdir(newLocation)


    # Find the domain origins for each of the sections and store them in a text file
    if not os.path.isfile("ORIGINAL_TRANSFORMATIONS.txt"):
        print("\nIdentifying and storing original transformations...")
        saveOriginalTransformations(seriesName, sectionNums)
    
    sectionInfo = {}
    for sectionNum in sectionNums:
        sectionInfo[sectionNum] = getSectionInfo(seriesName + "." + str(sectionNum))
        
    print("ORIGINAL_TRANSFORMATIONS.txt has been stored.")
    print("Do NOT delete this file.")

    # Create new trace files with shift domain origins

    print("\nCreating new domain origins file...")

    newTransformationsFile = open(newLocation + "/LOCAL_TRANSFORMATIONS.txt", "w")

    for sectionNum in sectionNums:
        
        # shift the domain origins to bottom left corner of planned crop
        orig_trans = coefToMatrix(sectionInfo[sectionNum][0], sectionInfo[sectionNum][1])
        min_coords = np.matmul(orig_trans, [[bounds_dict[sectionNum][0]],[bounds_dict[sectionNum][2]],[1]])
        pixPerMic = 1.0 / sectionInfo[sectionNum][2]
        xshift_pix = int((min_coords[0][0] - rad) * pixPerMic)
        if xshift_pix < 0:
            xshift_pix = 0
        yshift_pix = int((min_coords[1][0] - rad) * pixPerMic)
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

    print("\nCropping images around bounds...")

    for sectionNum in sectionNums:   
            
        fileName = sectionInfo[sectionNum][3]

        print("\nWorking on " + fileName + "...")
        
        # open original image
        img = PILImage.open(fileName)

        # get image dimensions
        img_length, img_height = img.size
        
        # get magnification
        pixPerMic = 1.0 / sectionInfo[sectionNum][2]
        
        # get the bounds coordinates in pixels
        orig_trans = coefToMatrix(sectionInfo[sectionNum][0], sectionInfo[sectionNum][1])
        min_coords = np.matmul(orig_trans, [[bounds_dict[sectionNum][0]],[bounds_dict[sectionNum][2]],[1]])
        max_coords = np.matmul(orig_trans, [[bounds_dict[sectionNum][1]],[bounds_dict[sectionNum][3]],[1]])

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
        cropped.save(newLocation + "/" + fileName)
        
        print("Saved!")

    print("\nCropping has run successfully!")

    print("\nSwitching to new crop...")
    switchToCrop(seriesName, obj)

    print("Successfully set " + obj + " as the focus.")
    
input("\nPress enter to exit.")
