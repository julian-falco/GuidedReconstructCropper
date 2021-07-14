from PIL import Image as PILImage
PILImage.MAX_IMAGE_PIXELS = None
import os
import numpy as np


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
                dim = int(lines[xcoefIndex-1].split('"')[1])
                if dim > 3:
                    raise Exception("This program cannot work with transformation dimensions higher than three.")
                
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
    prevCenter = (None, None)
    i = 0
    while prevCenter == (None, None):
        prevCenter = centers[i]
        i += 1
    
    # set any center points that are (None, None) to the previous center
    for i in range(len(centers)):
        if centers[i] == (None, None):
            centers[i] = prevCenter
        prevCenter = centers[i]
    
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
    dim = int(lines[domainIndex-5].split('"')[1])
    if dim > 3:
        raise Exception("This program cannot work with transformation dimensions higher than three.")

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
    sectionNum = [0,0]
    counter = 0
    lastSection = False
    firstSection = False
    
    # open files until unable to
    while not firstSection or not lastSection:
        try:
            f = open(seriesName + "." + str(counter))
            f.close()
            if not firstSection:
                sectionNum[0] = counter
                firstSection = True
            lastSection = False
        except:
            lastSection = True
        counter += 1
    
    sectionNum[1] = counter - 1
        
    return seriesName, sectionNum



def switchToOriginal(seriesName, sectionNum, objName):
    """Switch focus to a cropped series from the original"""

    # check for new transformations and undo them on each trace
    iDtransList = checkForRealignment(seriesName, objName)
    for i in range(len(iDtransList)):
        if iDtransList[i].any():
            transformAllTraces(seriesName + "." + str(i), iDtransList[i])

    # open the transformation files
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    newLocalTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "w")

    # store the new transformations
    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1])
        elif "Dtrans" in line:
            if iDtransList[sectionNum].any():
                # store the transformation matrix going from original to cropped
                Dtrans = np.linalg.inv(iDtransList[sectionNum])
                line = "Dtrans: "
                line += str(round(Dtrans[0,0],4)) + " "
                line += str(round(Dtrans[0,1],4)) + " "
                line += str(round(Dtrans[0,2],4)) + " "
                line += str(round(Dtrans[1,0],4)) + " "
                line += str(round(Dtrans[1,1],4)) + " "
                line += str(round(Dtrans[1,2],4)) + "\n"
                
        newLocalTrans.write(line)

    newLocalTrans.close()

    # go through each file and restore original domains and image sources

    origTrans = open("ORIGINAL_TRANSFORMATIONS.txt")
    lines = origTrans.readlines()
    origTrans.close()

    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1])
        elif "xcoef" in line:
            xcoef = [float(x) for x in line.split()[1:4]]
        elif "ycoef" in line:
            ycoef = [float(y) for y in line.split()[1:4]]

            newTraceFile(seriesName, sectionNum, "", xcoef, ycoef)
            

def switchToCrop(seriesName, sectionNum, objName):
    """Switch focus to an original series from a cropped one"""

    # save current alignment on original
    saveOriginalTransformations(seriesName, sectionNum)
    
    # open transformation files
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    origTrans = open("ORIGINAL_TRANSFORMATIONS.txt", "r")

    # grab transformation data from each of the files
    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1])
            origTrans.readline()
        elif "xshift" in line:
            xshift = float(line.split()[1])
            origLine = origTrans.readline()
            xcoef = [float(x) for x in origLine.split()[1:4]]
        elif "yshift" in line:
            yshift = float(line.split()[1])
            origLine = origTrans.readline()
            ycoef = [float(y) for y in origLine.split()[1:4]]
        elif "Dtrans" in line:
            Dtrans = [float(z) for z in line.split()[1:7]]
            DtransMatrix = [[Dtrans[0],Dtrans[1],Dtrans[2]],
                             [Dtrans[3],Dtrans[4],Dtrans[5]],
                             [0,0,1]]

            # transform all the traces by the Dtrans matrix
            transformAllTraces(seriesName + "." + str(sectionNum), DtransMatrix)

            # add the xshift and yshift to the transformation matrix and apply it to the domain
            domainTransMatrix = DtransMatrix.copy()
            domainTransMatrix[0][2] += xshift
            domainTransMatrix[1][2] += yshift
            
            origTransMatrix = coefToMatrix(xcoef, ycoef)
            
            newDomainTransMatrix = np.matmul(origTransMatrix, domainTransMatrix)

            # write the new domain transformation matrix to the domain in the section file
            new_xcoef = [newDomainTransMatrix[0][2], newDomainTransMatrix[0][0], newDomainTransMatrix[0][1]]
            new_ycoef = [newDomainTransMatrix[1][2], newDomainTransMatrix[1][0], newDomainTransMatrix[1][1]]
            
            newTraceFile(seriesName, sectionNum, objName, new_xcoef, new_ycoef)
            
    origTrans.close()
        
    
def checkForRealignment(seriesName, objName):
    """Check for differences in base alignment between cropped and original series"""

    # open the two transformation files
    origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "r")
    localTransFile = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")

    # read through each of the files and gather data
    iDtransList = []
    for localLine in localTransFile.readlines():
        if "Section" in localLine:
            origTransFile.readline()
            sectionNum = int(localLine.split()[1])
            if not iDtransList:
                iDtransList = [np.array([]) for i in range(sectionNum)]
            sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))
            local_xcoef = sectionInfo[0]
            local_ycoef = sectionInfo[1]
        elif "xshift" in localLine:
            origLine = origTransFile.readline()
            orig_xcoef = [float(x) for x in origLine.split()[1:7]]
            xshift = float(localLine.split()[1])
            local_xcoef[0] -= xshift
        elif "yshift" in localLine:
            origLine = origTransFile.readline()
            orig_ycoef = [float(y) for y in origLine.split()[1:7]]
            yshift = float(localLine.split()[1])
            local_ycoef[0] -= yshift

        # check for realignment using the two matrices
        elif "Dtrans" in localLine:
            # set up the two matrices
            local_matrix = coefToMatrix(local_xcoef, local_ycoef)
            orig_matrix = coefToMatrix(orig_xcoef, orig_ycoef)
            # get the "difference" between the two matrices and store the result
            z_matrix = np.matmul(orig_matrix, np.linalg.inv(local_matrix))
            iDtransList.append(z_matrix)
        
    origTransFile.close()
    localTransFile.close()

    return iDtransList

def transformAllTraces(fileName, transformation):
    """Multiply all of the traces on a section by a transformation matrix"""

    # open the section file    
    sectionFile = open(fileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()

    newSectionFile = open(fileName, "w")

    # read through the file
    for i in range(len(lines)):
        line = lines[i]
        if '<Transform dim="0"' in line:
            line = line.replace("0", "3")
        elif "xcoef" in line and "domain1" not in lines[i+4]:
            # gather the matrices and multiply them by the transformation matrix
            xcoef = [float(x) for x in line.split()[1:4]]
            ycoef = [float(y) for y in lines[i+1].split()[1:4]]
            newMatrix = np.matmul(transformation, coefToMatrix(xcoef, ycoef))

            # write the new matrices to the file
            
            xcoef_line = ' xcoef=" '
            xcoef_line += str(round(newMatrix[0,2],4)) + " "
            xcoef_line += str(round(newMatrix[0,0],4)) + " "
            xcoef_line += str(round(newMatrix[0,1],4)) + " "
            xcoef_line += '0 0 0"\n'

            ycoef_line = ' ycoef=" '
            ycoef_line += str(round(newMatrix[1,2],4)) + " "
            ycoef_line += str(round(newMatrix[1,0],4)) + " "
            ycoef_line += str(round(newMatrix[1,1],4)) + " "
            ycoef_line += '0 0 0">\n'

            line = xcoef_line
        
        elif "ycoef" in line and "domain1" not in lines[i+3]:
            line = ycoef_line

        newSectionFile.write(line)

    newSectionFile.close()

def coefToMatrix(xcoef, ycoef):
    """Turn a set of x and y coef into a transformation matrix"""
    
    return np.array([[xcoef[1], xcoef[2], xcoef[0]],
                       [ycoef[1], ycoef[2], ycoef[0]],
                       [0, 0, 1]])


def newTraceFile(seriesName, sectionNum, objName, xcoef, ycoef):
    """Creates a single new trace file with a shifted domain origin."""
    
    # open original trace file, read lines, and close
    fileName = seriesName + "." + str(sectionNum)
    sectionFile = open(fileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()
    
    # create new trace file
    newSectionFile = open(fileName, "w")

    # set up iterator
    domainIndex = 0
    line = lines[domainIndex]
    
    # check for domain in the text to find domain origin index
    while not '"domain1"' in line:
        domainIndex += 1
        line = lines[domainIndex]
        
    for i in range(len(lines)):
        
        # grab line
        line = lines[i]

        # make sure dimension is correct
        if i == domainIndex - 5 and 'dim="0"' in line:
            newSectionFile.write('<Transform dim="3"\n')
        
        # if the line is on the xcoef domain origin index, set x-shift
        elif i == domainIndex - 4:
            xcoef_str = ' xcoef="'
            for x in xcoef:
                xcoef_str += " " + str(round(x,4))
            xcoef_str += ' 0 0 0"'
            newSectionFile.write(xcoef_str + "\n")
            
        # if the line is on the ycoef domain origin index, set y-shift
        elif i == domainIndex - 3:
            ycoef_str = ' ycoef="'
            for y in ycoef:
                ycoef_str += " " + str(round(y,4))
            ycoef_str += ' 0 0 0">'
            newSectionFile.write(ycoef_str + "\n")

        # create a new image directory
        elif i == domainIndex - 1:
            imageFile = line.split('"')[1]
            if "/" in imageFile:
                imageFile = imageFile[imageFile.find("/")+1:]
            if not objName == "":
                imageFile = seriesName + "_" + objName + "/" + imageFile
            newSectionFile.write(' src="' + imageFile + '" />\n')
                
        # otherwise, copy the file exactly as is
        else:
            newSectionFile.write(line)
            
    newSectionFile.close()

def getCropFocus(sectionFileName):
    """Find the current crop the Reconstruct is focusing on"""

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
        cropFocus = imageFile[imageFile.find("_")+1:imageFile.find("/")]
    else:
        cropFocus = ""

    return cropFocus

def saveOriginalTransformations(seriesName, sectionNum):
    transformationsFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")
    for i in range(sectionNum[0], sectionNum[1]):
        sectionInfo = getSectionInfo(seriesName + "." + str(i))
        xcoef_str = ""
        for x in sectionInfo[0]:
            xcoef_str += str(round(x,4)) + " "
        ycoef_str = ""
        for y in sectionInfo[1]:
            ycoef_str += str(round(y,4)) + " "
        transformationsFile.write("Section " + str(i) + "\n"
                                  "xcoef: " + xcoef_str + "\n" +
                                  "ycoef: " + ycoef_str + "\n")
    transformationsFile.close()

# BEGINNING OF MAIN: gather inputs
##try:

# locate the series file and gather pertinent info
for file in os.listdir("."):
    if file.endswith(".ser"):
        fileName = str(file)
seriesName, sectionNum = getSeriesInfo(fileName)

# find the current crop focus
cropFocus = getCropFocus(seriesName + "." + str(sectionNum[0]))
if cropFocus:
    print("This series is currently focused on: " + cropFocus + "\n")
else:
    print("This series is currently set to the original set of images.\n")

# gather inputs
print("Please enter the name of the object you would like to focus on.")
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
            input("Press enter to continue or Ctrl+c to exit.\n")
            switchToOriginal(seriesName, sectionNum, cropFocus)
            print("Successfully set the original series as the focus.\n")

    # if switching to existing crop
    else:
        if cropFocus == obj:
            print("\n" + obj + " is already set as the focus.")
        else:
            if cropFocus != "":
                # switch to the original crop if not already on
                switchToOriginal(seriesName, sectionNum, cropFocus)
            print("\nA cropped set of images for this object exists.")
            input("Press enter to continue and switch cropping focus to this object.\n")
            switchToCrop(seriesName, sectionNum, obj)
            print("Successfully set " + obj + " as the focus.\n")

# cropping a new set of images
else:
    print("\nThere does not appear to be an existing set of cropped pictures.")
    input("Press enter to continue and create them.")

    # switch to the original and set the crop focus as such if not already
    if os.path.isfile("ORIGINAL_TRANSFORMATIONS.txt") and cropFocus != "":
        switchToOriginal(seriesName, sectionNum, cropFocus)
        cropFocus = ""

    # Find the center points for the object and fill in missing centers

    print("\nLocating the object...")

    centers = []
    for i in range(sectionNum[0]):
        centers.append(None)
    for i in range(sectionNum[0], sectionNum[1]):
        centers.append(findCenter(seriesName + "." + str(i), obj))

    # check to see if the object was found, raise exception if not
    noTraceFound = True
    for center in centers:
        if center != (0,0) and center != None:
            noTraceFound = False
    if noTraceFound:
        raise Exception("This trace does not exist in this series.")

    centers = fillInCenters(centers)

    print("Completed successfully!\n")

    # ask the user for the cropping rad
    rad = float(input("What is the cropping radius in microns?: "))

    newLocation = seriesName + "_" + obj
    os.mkdir(newLocation)


    # Find the domain origins for each of the sections and store them in a text file

    print("\nIdentifying and storing domain origins...")
    saveOriginalTransformations(seriesName, sectionNum)
    
    sectionInfo = []
    for i in range(sectionNum[0]):
        sectionInfo.append(None)
    for i in range(sectionNum[0], sectionNum[1]):
        sectionInfo.append(getSectionInfo(seriesName + "." + str(i)))
        
    print("ORIGINAL_TRANSFORMATIONS.txt has been stored.\nDo NOT delete this file.\n")

    # Create new trace files with shift domain origins

    print("Creating new domain origins file...")

    newTransformationsFile = open(newLocation + "/LOCAL_TRANSFORMATIONS.txt", "w")

    for i in range(sectionNum[0], sectionNum[1]):
        
        # shift the domain origins to bottom left corner of planned crop
        xshift = sectionInfo[i][0][0] + centers[i][0] - rad
        xshift *= -1
        
        yshift = sectionInfo[i][1][0] + centers[i][1] - rad
        yshift *= -1

        newTransformationsFile.write("Section " + str(i) + "\n" +
                                     "xshift: " + str(round(xshift,4)) + "\n" +
                                     "yshift: " + str(round(yshift,4)) + "\n" +
                                     "Dtrans: 1 0 0 0 1 0\n")

    newTransformationsFile.close()

    print("LOCAL_TRANSFORMATIONS.txt has been stored.\nDo NOT delete this file.\n")



    # Crop each image

    print("Cropping images around centers...\n")

    for i in range(sectionNum[0], sectionNum[1]):
        
        if not centers[i] == (0, 0):
            
            fileName = sectionInfo[i][3]

            print("Working on " + fileName + "...")
            
            # open original image with cv2 (PIL cannot handle large images)
            img = PILImage.open(fileName)

            # get image dimensions
            img_length, img_height = img.size
            
            # get magnification
            pixPerMic = 1.0 / sectionInfo[i][2]
            
            # get the cropping radius in pixels
            pixRad = rad * pixPerMic
            
            # get the center coordinates in pixels
            pixx = (centers[i][0] + sectionInfo[i][0][0]) * pixPerMic
            pixy = img_height - (centers[i][1] + sectionInfo[i][1][0]) * pixPerMic
            
            # get the pixel coordinates for each corner of the crop
            left = int(pixx - pixRad)
            right = int(pixx + pixRad)
            top = int(pixy - pixRad)
            bottom = int(pixy + pixRad)

            # if crop exceeds image boundary, cut it off
            if left < 0: left = 0
            if right >= img_length: right = img_length-1
            if top < 0: top = 0
            if bottom >= img_height: bottom = img_height-1

            # crop the photo
            cropped = img.crop((left, top, right, bottom))
            cropped.save(newLocation + "/" + fileName)
            
            print("Saved!\n")

    print("Cropping has run successfully!\n")

    switchToCrop(seriesName, sectionNum, obj)

    print("Successfully set " + obj + " as the focus.\n")
    
input("\nPress enter to exit.")
