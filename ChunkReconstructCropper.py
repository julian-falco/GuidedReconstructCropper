from PIL import Image as PILImage
PILImage.MAX_IMAGE_PIXELS = None
import os
import numpy as np
from tkinter import *
from tkinter.filedialog import askopenfilenames


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
fileName = ""
for file in os.listdir("."):
    if file.endswith(".ser"):
        fileName = str(file)

# switch crops if there is an existing series file
if fileName:
    seriesName, sectionNum = getSeriesInfo(fileName)

    # find the current crop focus
    cropFocus = getCropFocus(seriesName + "." + str(sectionNum[0]))
    if cropFocus:
        print("This series is currently focused on: " + cropFocus)
    else:
        print("This series is currently set to the original set of images.")

    # gather inputs
    print("Please enter the coordinates you would like to focus on.")
    chunkCoords = input("(x,y with no spaces or parentheses): ")

    # if switching to original
    if chunkCoords == "":
        if cropFocus == "":
            print("\nThe original series is already set as the focus.")
        else:
            print("\nWould you like to switch to the original series?")
            input("Press enter to continue or Ctrl+c to exit.\n")
            switchToOriginal(seriesName, sectionNum, cropFocus)
            print("Successfully set the original series as the focus.\n")

    # if switching to existing crop
    else:
        if cropFocus == chunkCoords:
            print("\n" + obj + " is already set as the focus.")
        else:
            if os.path.isdir(seriesName + "_" + str(chunkCoords)):
                if cropFocus != "":
                    # switch to the original crop if not already on
                    switchToOriginal(seriesName, sectionNum, cropFocus)
                input("Press enter to continue and switch cropping focus to this chunk.\n")
                switchToCrop(seriesName, sectionNum, chunkCoords)
                print("Successfully set " + chunkCoords + " as the focus.\n")
            else:
                print("These chunk coordinates are not found in this series.")

# cropping a new set of images if there is no detected series file
else:
    print("\nThere does not appear to be an existing set of cropped pictures.")
    seriesName = input("Please enter the name of the series: ")
    input("Press enter to select the pictures you would like to crop.\n")

    Tk().withdraw()
    imageFiles = list(askopenfilenames(title="Select Image Files",
                               filetypes=(("Image Files", "*.tif"),
                                          ("All Files","*.*"))))
    
    xchunks = int(input("How many horizontal chunks would you like to have?: "))
    ychunks = int(input("How many vertical chunks would you like to have?: "))

    micPerPix = float(input("How many microns per pixel are there for this series?: "))
    sectionThickness = float(input("What would you like to set as the section thickness?: "))
    overlap = float(input("How many microns of overlap should there be between chunks?: "))

    # find the corner coordinates for each of the chunks (in microns)

    # store domain origins for each of the sections and store them in a text file
    
    origTransFile = open("ORIGINAL_TRANSFORMATIONS.txt", "w")
    
    for i in range(len(imageFiles)):
        origTransFile.write("Section " + str(i) + "\n" +
                                  "xcoef: 0 1 0 0 0 0\n" +
                                  "ycoef: 0 0 1 0 0 0\n")        
    origTransFile.close()

    print("ORIGINAL_TRANSFORMATIONS.txt has been stored.\nDo NOT delete this file.")

    print("Completed successfully!\n")


    # create each folder
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
        
        # format the image files and rename them
        #os.rename(imageFiles[i], seriesName + "." + str(i) + ".tif")
        #imageFiles[i] = seriesName + "." + str(i) + ".tif"

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
                
                left = int(img_length * x / xchunks - overlap/2 / micPerPix)
                if left < 0:
                    left = 0
                right = int(img_length * (x+1) / xchunks + overlap/2 / micPerPix)
                if right >= img_length:
                    right = img_length - 1
                
                top = int(img_height * (ychunks - y-1) / ychunks - overlap/2 / micPerPix)
                if top < 0:
                      top = 0 
                bottom = int(img_height * (ychunks - y) / ychunks + overlap/2 / micPerPix)
                if bottom >= img_height:
                    bottom = img_height - 1

                # crop the photo
                cropped = img.crop((left, top, right, bottom))
                
                newDomainOrigins[x].append((left * micPerPix, (img_height - (bottom+1)) * micPerPix))

                # cv2 can only save compressed TIF, so convert array to PIL object and save as uncompressed TIF
                cropped.save(seriesName + "_" + str(x) + "," + str(y) + "/" +
                         seriesName + "." + str(i) + ".tif")


    # Create new local transformations files

    print("Creating new domain origins files...")

    for x in range(xchunks):
        for y in range(ychunks):
            newTransformationsFile = open(seriesName + "_" + str(x) + "," + str(y) +
                                         "/LOCAL_TRANSFORMATIONS.txt", "w")
            for i in range(len(imageFiles)):
                
                # shift the domain origins to bottom left corner of planned crop
                xshift = -newDomainOrigins[x][y][0]
                yshift = -newDomainOrigins[x][y][1]
                newTransformationsFile.write("Section " + str(i) + "\n" +
                                             "xshift: " + str(round(xshift,4)) + "\n" +
                                             "yshift: " + str(round(yshift,4)) + "\n" +
                                             "Dtrans: 1 0 0 0 1 0\n")
            newTransformationsFile.close()

    # create blank section and series files

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
    blankSectionFile = blankSectionFile.replace("[XCOEF]", " 0 1 0 0 0 0")
    blankSectionFile = blankSectionFile.replace("[YCOEF]", " 0 0 1 0 0 0")
    blankSectionFile = blankSectionFile.replace("[IMAGE_MAG]", str(micPerPix))
    blankSectionFile = blankSectionFile.replace("[IMAGE_LENGTH]", str(int(img_length_max / xchunks)))
    blankSectionFile = blankSectionFile.replace("[IMAGE_HEIGHT]", str(int(img_height_max / ychunks)))

    
    
    for i in range(len(imageFiles)):
        newSectionFile = open(seriesName + "." + str(i), "w")
        
        sectionFileText = blankSectionFile.replace("[SECTION_INDEX]", str(i))
        sectionFileText = sectionFileText.replace("[IMAGE_SOURCE]", seriesName + "." + str(i) + ".tif")

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

    sectionNum = getSeriesInfo(seriesName)[1]
    #switchToCrop(seriesName, sectionNum, "0,0")
    
input("\nPress enter to exit.")
