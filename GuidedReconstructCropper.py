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
            xshift = float(line.split()[1])
        elif "yshift" in line:
            yshift = float(line.split()[1])
            
        elif "Dtrans" in line:
            # edit all of the traces in the section
            transformAllTraces(seriesName + "." + str(sectionNum),
                               iDtransList[sectionNum],
                               -xshift, -yshift, "")
            
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
            xshift = float(line.split()[1])
        elif "yshift" in line:
            yshift = float(line.split()[1])
        elif "Dtrans" in line:
            Dtrans = [float(z) for z in line.split()[1:7]]
            DtransMatrix = [[Dtrans[0],Dtrans[1],Dtrans[2]],
                                 [Dtrans[3],Dtrans[4],Dtrans[5]],
                                 [0,0,1]]

            # transform all the traces by the Dtrans matrix
            transformAllTraces(seriesName + "." + str(sectionNum), DtransMatrix, xshift, yshift, objName)
        
    
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
            for row in range(len(z_matrix)):
                for col in range(len(z_matrix)):
                    z_matrix[row][col] = round(z_matrix[row][col],4)
            iDtransList[sectionNum] = z_matrix
        
    origTransFile.close()
    localTransFile.close()

    return iDtransList


def transformAllTraces(fileName, transformation, xshift, yshift, objName):
    """Multiply all of the traces on a section by a transformation matrix while also changing the image domain and source"""

    # check if transformation is needed
    transformation = np.array(transformation)
    noTrans = np.array([[1,0,0],[0,1,0],[0,0,1]])
    needsTransformation = not (transformation == noTrans).all()
    
    # make the domain transformation matrix
    domainTransformation = transformation.copy()
    domainTransformation[0][2] += xshift
    domainTransformation[1][2] += yshift
    
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
            newMatrix = np.matmul(domainTransformation, coefToMatrix(xcoef, ycoef))

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
        
        elif needsTransformation and "ycoef" in line:
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
        cropFocus = imageFile[imageFile.find("_")+1:imageFile.find("/")]
    else:
        cropFocus = ""

    return cropFocus


def saveOriginalTransformations(seriesName, sectionNums):
    transformationsFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")
    for sectionNum in sectionNums:
        sectionInfo = getSectionInfo(seriesName + "." + str(sectionNum))
        xcoef_str = ""
        for x in sectionInfo[0]:
            xcoef_str += str(round(x,4)) + " "
        ycoef_str = ""
        for y in sectionInfo[1]:
            ycoef_str += str(round(y,4)) + " "
        transformationsFile.write("Section " + str(sectionNum) + "\n"
                                  "xcoef: " + xcoef_str + "\n" +
                                  "ycoef: " + ycoef_str + "\n")
    transformationsFile.close()



# BEGINNING OF MAIN: gather inputs

print("Locating series file...")
# locate the series file and gather pertinent info
for file in os.listdir("."):
    if file.endswith(".ser"):
        fileName = str(file)
seriesName, sectionNums = getSeriesInfo(fileName)

# find the current crop focus
print("Finding crop focus...")
cropFocus = getCropFocus(seriesName + "." + str(sectionNums[0]))
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

    # Find the center points for the object and fill in missing centers

    print("\nLocating the object...")

    centers = {}
    for sectionNum in sectionNums:
        centers[sectionNum] = findCenter(seriesName + "." + str(sectionNum), obj)

    # check to see if the object was found, raise exception if not
    noTraceFound = True
    for center in centers:
        if center != (0,0) and center != None:
            noTraceFound = False
    if noTraceFound:
        raise Exception("This trace does not exist in this series.")

    centers = fillInCenters(centers)

    print("Completed successfully!")

    # ask the user for the cropping rad
    rad = float(input("\nWhat is the cropping radius in microns?: "))

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
        xshift = -(sectionInfo[sectionNum][0][0] + centers[sectionNum][0] - rad)
        
        yshift = -(sectionInfo[sectionNum][1][0] + centers[sectionNum][1] - rad)

        newTransformationsFile.write("Section " + str(sectionNum) + "\n" +
                                     "xshift: " + str(round(xshift,4)) + "\n" +
                                     "yshift: " + str(round(yshift,4)) + "\n" +
                                     "Dtrans: 1 0 0 0 1 0\n")

    newTransformationsFile.close()

    print("LOCAL_TRANSFORMATIONS.txt has been stored.")
    print("Do NOT delete this file.")

    # Crop each image

    print("\nCropping images around centers...")

    for sectionNum in sectionNums:   
            
        fileName = sectionInfo[sectionNum][3]

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
        pixx = (centers[sectionNum][0] + sectionInfo[sectionNum][0][0]) * pixPerMic
        pixy = img_height - (centers[sectionNum][1] + sectionInfo[sectionNum][1][0]) * pixPerMic
        
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
        
        print("Saved!")

    print("\nCropping has run successfully!")

    print("\nSwitching to new crop...")
    switchToCrop(seriesName, obj)

    print("Successfully set " + obj + " as the focus.")
    
input("\nPress enter to exit.")
