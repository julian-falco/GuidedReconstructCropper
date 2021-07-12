from PIL import Image
import cv2
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
                    raise Exception("This program cannot work with transformation dimesnsions higher than three.")
                
                # set the xcoef and ycoef
                xcoef = [float(x) for x in lines[xcoefIndex].split()[1:4]]
                ycoef = [float(y) for y in lines[xcoefIndex+1].split()[1:4]]
    
    # if the trace is not found in the section
    if total == 0:
        return 0,0
    
    # return averages reounded to five decimal points
    return round(xsum/total, 5), round(ysum/total, 5)



def fillInCenters(centers):
    """Fills in center data where object doesn't exist with center data from previous sections."""
    
    # if the first section(s) do not have the object, then fill it in with first object instance
    prevCenter = (0,0)
    i = 0
    while prevCenter == (0,0):
        prevCenter = centers[i]
        i += 1
    
    # set any center points that are (0,0) to the previous center
    for i in range(len(centers)):
        if centers[i] == (0,0):
            centers[i] = prevCenter
        prevCenter = centers[i]
        i += 1
    
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

    
    # grab x and y coords for domain origin
    dim = int(lines[domainIndex-5].split('"')[1])
    if dim > 3:
        raise Exception("This program cannot work with transformation dimesnsions higher than three.")
    
    xcoef = []
    for x in lines[domainIndex-4].replace('"',"").split()[1:7]:
        if float(x) % 1 == 0:
            xcoef.append(int(x))
        else:
            xcoef.append(round(float(x), 4))

    ycoef = []
    for y in lines[domainIndex-3].replace('">',"").split()[1:7]:
        if float(y) % 1 == 0:
            ycoef.append(int(y))
        else:
            ycoef.append(round(float(y), 4))
    
    mag = float(lines[domainIndex-2].split('"')[1])
    src = lines[domainIndex-1].split('"')[1]    

    return xcoef, ycoef, mag, src

    
    
def getSeriesInfo(fileName):
    """Return the series name and section number"""

    # split up the name and file path
    seriesName = fileName.replace(".ser", "")
    
    # find out how many sections there are
    sectionNum = [0,0]
    counter = 0
    lastSection = False
    firstSection = False
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



def switchToOriginal(seriesName, objName):

    # check for new transformations and undo them on each trace
    
    ztransList = checkForRealignment(seriesName, objName)

    for i in range(len(ztransList)):
        if ztransList[i].any():
            transformAllTraces(seriesName + "." + str(i), ztransList[i])

    # store the new transformations
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    newLocalTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "w")

    for line in lines:
        if "Section" in line:
            sectionNum = int(line.split()[1])
        elif "iztrans" in line:
            if ztransList[sectionNum].any():
                iztrans = np.linalg.inv(ztransList[sectionNum])
                line = "iztrans: "
                line += str(round(iztrans[0,0],4)) + " "
                line += str(round(iztrans[0,1],4)) + " "
                line += str(round(iztrans[0,2],4)) + " "
                line += str(round(iztrans[1,0],4)) + " "
                line += str(round(iztrans[1,1],4)) + " "
                line += str(round(iztrans[1,2],4)) + "\n"
                
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
            xcoef = [float(x) for x in line.split()[1:7]]
        elif "ycoef" in line:
            ycoef = [float(y) for y in line.split()[1:7]]

            newTraceFile(seriesName, sectionNum, "", xcoef, ycoef)
            

def switchToCrop(seriesName, objName):

    # get the local transformations saved and apply them to the traces
    # also edit trace files to change domain and source
    localTrans = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    lines = localTrans.readlines()
    localTrans.close()

    origTrans = open("ORIGINAL_TRANSFORMATIONS.txt", "r")

    
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
        elif "iztrans" in line:
            iztrans = [float(z) for z in line.split()[1:7]]
            iztransMatrix = [[iztrans[0],iztrans[1],iztrans[2]],
                             [iztrans[3],iztrans[4],iztrans[5]],
                             [0,0,1]]
            transformAllTraces(seriesName + "." + str(sectionNum), iztransMatrix)

            domainTransMatrix = iztransMatrix.copy()
            domainTransMatrix[0][2] += xshift
            domainTransMatrix[1][2] += yshift
            
            origTransMatrix = coefToMatrix(xcoef, ycoef)
            
            newDomainTransMatrix = np.matmul(origTransMatrix, domainTransMatrix)
            
            new_xcoef = [newDomainTransMatrix[0][2], newDomainTransMatrix[0][0], newDomainTransMatrix[0][1], 0, 0, 0]
            new_ycoef = [newDomainTransMatrix[1][2], newDomainTransMatrix[1][0], newDomainTransMatrix[1][1], 0, 0, 0]
            
            newTraceFile(seriesName, sectionNum, objName, new_xcoef, new_ycoef)
            
    origTrans.close()
        
    
def checkForRealignment(seriesName, objName):
    origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "r")
    localTransFile = open(seriesName + "_" + objName + "/LOCAL_TRANSFORMATIONS.txt", "r")
    ztransList = []
    for localLine in localTransFile.readlines():
        if "Section" in localLine:
            origTransFile.readline()
            sectionNum = int(localLine.split()[1])
            if not ztransList:
                ztransList = [np.array([]) for i in range(sectionNum)]
            sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))
            local_xcoef = sectionInfo[0]
            local_ycoef = sectionInfo[1]
        elif "xshift" in localLine:
            origLine = origTransFile.readline()
            orig_xcoef = [round(float(x),4) for x in origLine.split()[1:7]]
            xshift = round(float(localLine.split()[1]),4)
            local_xcoef[0] -= xshift
        elif "yshift" in localLine:
            origLine = origTransFile.readline()
            orig_ycoef = [round(float(y),4) for y in origLine.split()[1:7]]
            yshift = round(float(localLine.split()[1]),4)
            local_ycoef[0] -= yshift
        elif "iztrans" in localLine:
            local_matrix = coefToMatrix(local_xcoef, local_ycoef)
            orig_matrix = coefToMatrix(orig_xcoef, orig_ycoef)
            z_matrix = np.matmul(orig_matrix, np.linalg.inv(local_matrix))
            ztransList.append(z_matrix)
    origTransFile.close()
    localTransFile.close()

    return ztransList

def transformAllTraces(fileName, transformation):
    sectionFile = open(fileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()

    newSectionFile = open(fileName, "w")
    
    for i in range(len(lines)):
        line = lines[i]
        if '<Transform dim="0"' in line:
            line = line.replace("0", "3")
        elif "xcoef" in line and "domain1" not in lines[i+4]:
            xcoef = [float(x) for x in line.split()[1:4]]
            ycoef = [float(y) for y in lines[i+1].split()[1:4]]
            newMatrix = np.matmul(transformation, coefToMatrix(xcoef, ycoef))
            
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
        
        elif "ycoef" in line and "domain1" not in lines[i+3]:
            line = ycoef_line

        newSectionFile.write(line)

    newSectionFile.close()

def coefToMatrix(xcoef, ycoef):
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
                if x % 1 == 0:
                    xcoef_str += " " + str(int(x))
                else:
                    xcoef_str += " " + str(x)
            xcoef_str += '"'
            newSectionFile.write(xcoef_str + "\n")
            
        # if the line is on the ycoef domain origin index, set y-shift
        elif i == domainIndex - 3:
            ycoef_str = ' ycoef="'
            for y in ycoef:
                if y % 1 == 0:
                    ycoef_str += " " + str(int(y))
                else:
                    ycoef_str += " " + str(y)
            ycoef_str += '">'
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
    sectionFile = open(sectionFileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()

    lineIndex = 0

    while 'src="' not in lines[lineIndex]:
        lineIndex += 1

    imageFile = lines[lineIndex].split('"')[1]

    if "/" in imageFile:
        cropFocus = imageFile[imageFile.find("_")+1:imageFile.find("/")]
    else:
        cropFocus = ""

    return cropFocus



# BEGINNING OF MAIN: gather inputs
##try:
# locate the series file and gather pertinent info
for file in os.listdir("."):
    if file.endswith(".ser"):
        fileName = str(file)
seriesName, sectionNum = getSeriesInfo(fileName)

print("Please enter the name of the object you would like to focus on.")
obj = input("(enter nothing if you would like to focus on the original series): ")
cropFocus = getCropFocus(seriesName + "." + str(sectionNum[0]))

if os.path.isdir(seriesName + "_" + obj) or obj == "":
    if obj == "":
        if cropFocus == "":
            print("\nThe original series is already set as the focus.")
        else:
            print("\nWould you like to switch to the original series?")
            input("Press enter to continue or Ctrl+c to exit.\n")
            switchToOriginal(seriesName, cropFocus)
            print("Successfully set the original series as the focus.\n")
    else:
        if cropFocus == obj:
            print("\n" + obj + " is already set as the focus.")
        else:
            if cropFocus != "":
                switchToOriginal(seriesName, cropFocus)
            print("\nA cropped set of images for this object exists.")
            input("Press enter to continue and switch cropping focus to this object.\n")
            switchToCrop(seriesName, obj)
            print("Successfully set " + obj + " as the focus.\n")
    
else:
    print("\nThere does not appear to be an existing set of cropped pictures.")
    input("Press enter to continue and create them.")

    if os.path.isfile("ORIGINAL_TRANSFORMATIONS.txt") and cropFocus != "":
        switchToOriginal(seriesName, cropFocus)
        cropFocus = ""

    # Find the center points for the object and fill in missing centers

    print("\nIdentifying center points for the object...")

    centers = []
    for i in range(sectionNum[0]):
        centers.append(None)
    for i in range(sectionNum[0], sectionNum[1]):
        centers.append(findCenter(seriesName + "." + str(i), obj))

    noTraceFound = True
    for center in centers:
        if center != (0,0) and center != None:
            noTraceFound = False
    if noTraceFound:
        raise Exception("This trace does not exist in this series.")

    centers = fillInCenters(centers)

    print("Completed successfully!\n")


    rad = float(input("\nWhat is the cropping radius in microns?: "))

    newLocation = seriesName + "_" + obj
    os.mkdir(newLocation)


    # Find the domain origins for each of the sections and store them in a text file

    print("Identifying and storing domain origins...")

    sectionInfo = []
    for i in range(sectionNum[0]):
        sectionInfo.append(None)
    for i in range(sectionNum[0], sectionNum[1]):
        sectionInfo.append(getSectionInfo(seriesName + "." + str(i)))

    if not os.path.isfile("ORIGINAL_TRANSFORMATIONS.txt"):

        transformationsFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")

        for i in range(sectionNum[0], sectionNum[1]):
            xcoef_str = ""
            for x in sectionInfo[i][0]:
                xcoef_str += str(x) + " "
            ycoef_str = ""
            for y in sectionInfo[i][1]:
                ycoef_str += str(y) + " "
            transformationsFile.write("Section " + str(i) + "\n"
                                      "xcoef: " + xcoef_str + "\n" +
                                      "ycoef: " + ycoef_str + "\n")
            
        transformationsFile.close()

        print("ORIGINAL_TRANSFORMATIONS.txt has been stored.\nDo NOT delete this file.")

        print("Completed successfully!\n")



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
                                     "iztrans: 1 0 0 0 1 0\n")

    newTransformationsFile.close()


    # Crop each image

    print("Cropping images around centers...\n")

    for i in range(sectionNum[0], sectionNum[1]):
        
        if not centers[i] == (0, 0):
            
            fileName = sectionInfo[i][3]

            print("Working on " + fileName + "...")
            
            # open original image with cv2 (PIL cannot handle large images)
            img = cv2.imread(fileName)
            
            # get magnification
            pixPerMic = 1.0 / sectionInfo[i][2]
            
            # get the cropping radius in pixels
            pixRad = rad * pixPerMic
            
            # get the center coordinates in pixels
            pixx = (centers[i][0] + sectionInfo[i][0][0]) * pixPerMic
            pixy = img.shape[0] - (centers[i][1] + sectionInfo[i][1][0]) * pixPerMic
            
            # get the pixel coordinates for each corner of the crop
            left = int(pixx - pixRad)
            right = int(pixx + pixRad)
            top = int(pixy - pixRad)
            bottom = int(pixy + pixRad)

            # if crop exceeds image boundary, cut it off
            if left < 0: left = 0
            if right >= img.shape[1]: right = img.shape[1]-1
            if top < 0: top = 0
            if bottom >= img.shape[0]: bottom = img.shape[0]-1

            # crop the photo (numpy slice)
            cropped = img[top:bottom, left:right, 0]
        
            # cv2 can only save compressed TIF, so convert array to PIL object and save as uncompressed TIF
            img = Image.fromarray(cropped)
            img.save(newLocation + "/" + fileName)
            
            print("Saved!\n")

    print("Cropping has run successfully!\n")

    switchToCrop(seriesName, obj)

    print("Successfully set " + obj + " as the focus.\n")
    
input("\nPress enter to exit.")
