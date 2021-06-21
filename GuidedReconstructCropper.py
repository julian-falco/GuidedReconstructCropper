from PIL import Image
import cv2



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
            
            # check if there are still points there and add to sum (with xcoef and ycoef offset)
            if len(coords) == 2:
                xsum += float(coords[0]) - xcoef
                ysum += float(coords[1]) - ycoef
            
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
                
                # set the xcoef and ycoef
                xcoef = float(lines[xcoefIndex].split()[1])
                ycoef = float(lines[xcoefIndex+1].split()[1])
    
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



def getDomainOrigin(fileName):
    """Gets the domain origin data from a single trace file."""
    
    # open trace file, read lines, and close
    traceFile = open(fileName, "r")
    lines = traceFile.readlines()
    traceFile.close()
    
    # set up iterator
    lineIndex = 0
    line = lines[lineIndex]
    
    # check for domain in the text to find domain origin index
    while not '"domain1"' in line:
        lineIndex += 1
        line = lines[lineIndex]
    
    # origin points are actually four lines before "domain1" is mentioned in text
    domainIndex = lineIndex - 4
    
    # grab x and y coords for domain origin
    xcoef = float(lines[domainIndex].split()[1])
    ycoef = float(lines[domainIndex+1].split()[1])

    return xcoef, ycoef, domainIndex



def restoreDomainOrigin(fileName, xcoef, ycoef):
    """Changes the domain origin on a single trace file to the specified values."""
    
    # open trace file, read lines, and close
    croppedTraceFile = open(fileName, "r")
    lines = croppedTraceFile.readlines()
    croppedTraceFile.close()
    
    # set up iterator
    lineIndex = 0
    line = lines[lineIndex]
    
    # check for domain in the text to find domain origin index
    while not '"domain1"' in line:
        lineIndex += 1
        line = lines[lineIndex]
    
    # origin points are actually four lines before "domain1" is mentioned in text
    domainIndex = lineIndex - 4
    
    # create new trace file (overwrites cropped trace file)
    restoredTraceFile = open(fileName, "w")
    
    for i in range(len(lines)):
        
        # grab line
        line = lines[i]
        
        # if the line is on the xcoef domain origin index, change xcoef
        if i == domainIndex:
            splitLine = line.split()
            splitLine[1] = str(xcoef)
            restoredTraceFile.write(" " + " ".join(splitLine) + "\n")
            
        # if the line is on the ycoef domain origin index, change ycoef
        elif i == domainIndex + 1:
            splitLine = line.split()
            splitLine[1] = str(ycoef)
            restoredTraceFile.write(" " + " ".join(splitLine) + "\n")
        
        # otherwise, copy the file exactly as is
        else:
            restoredTraceFile.write(line)
    
    restoredTraceFile.close()



def newTraceFile(fileName, newFileName, xshift, yshift, domainIndex):
    """Creates a single new trace file with a shifted domain origin."""
    
    # open original trace file, read lines, and close
    sectionFile = open(fileName, "r")
    lines = sectionFile.readlines()
    sectionFile.close()
    
    # create new trace file
    newSectionFile = open(newFileName, "w")
    
    
    for i in range(len(lines)):
        
        # grab line
        line = lines[i]
        
        # if the line is on the xcoef domain origin index, set x-shift
        if i == domainIndex:
            splitLine = line.split()
            xcoef = float(splitLine[1])
            xcoef += xshift
            splitLine[1] = str(round(xcoef, 5))
            newSectionFile.write(" " + " ".join(splitLine) + "\n")
            
        # if the line is on the ycoef domain origin index, set y-shift
        elif i == domainIndex + 1:
            splitLine = line.split()
            ycoef = float(splitLine[1])
            ycoef += yshift
            splitLine[1] = str(round(ycoef, 5))
            newSectionFile.write(" " + " ".join(splitLine) + "\n")
        
        # otherwise, copy the file exactly as is
        else:
            newSectionFile.write(line)
            
    newSectionFile.close()



# BEGINNING OF MAIN: gather inputs

seriesName = input("What is the name of this series?: ")
sectionNum = int(input("What is the number of sections in this series? (make sure to include the 0 section): "))
obj = input("What is the name of the object on which the crop should be centered?: ")
rad = float(input("What is the cropping radius in microns?: "))
pixPerMic = float(input("What is the number of pixels per micron in this series?: "))
oldLocation = input("What is the file path for the folder containing the original series?: ")
newLocation = input("What is the file path for the empty folder to contain the new series?: ")

# requires that the two folder locations be different so that data is not overridden
while oldLocation == newLocation:
    print("The file path for the original series and the new series cannot be the same")
    oldLocation = input("What is the file path for the folder containing the original series?: ")
    newLocation = input("What is the file path for the empty folder to contain the new series?: ")



# Find the center points for the object and fill in missing centers

print("Identifying center points for the object...")

centers = []

for i in range(sectionNum):
    centers.append(findCenter(oldLocation + '\\' + seriesName + "." + str(i), obj))

centers = fillInCenters(centers)

print("Completed successfully!")



# Find the domain origins for each of the sections and store them in a text file

print("Identifying and storing domain origins...")

domainOrigins = []

for i in range(sectionNum):
    domainOrigins.append(getDomainOrigin(oldLocation + '\\' + seriesName + "." + str(i)))

domainOriginsFile = open(newLocation + "\\ORIGINAL_DOMAIN_ORIGINS.txt", "w")

for i in range(sectionNum):
    domainOriginsFile.write(str(domainOrigins[i][0]) + " "
                            + str(domainOrigins[i][1]) + "\n")
domainOriginsFile.close()

print("ORIGINAL_DOMAIN_ORIGINS.txt has been stored in the new folder.\nDo NOT delete this file.")

print("Completed successfully!")



# Create new trace files with shift domain origins

print("Creating new trace files...")

for i in range(sectionNum):
    
    # shift the domain origins to bottom left corner of planned crop
    shift = (centers[i][0] + domainOrigins[i][0] - rad,
             centers[i][1] + domainOrigins[i][1] - rad)
    
    # create the new trace file (invert the shifts so the picture moves in the correct direction)
    newTraceFile(oldLocation + "\\" + seriesName + "." + str(i),
                 newLocation + "\\" + seriesName + "." + str(i),
                 shift[0] * -1,
                 shift[1] * -1,
                 domainOrigins[i][2])

# Copy series file
    
print("Copying original series file...")

oldSeriesFile = open(oldLocation + "\\" + seriesName + ".ser", "r")
newSeriesFile = open(newLocation + "\\" + seriesName + ".ser", "w")

for line in oldSeriesFile.readlines():
    newSeriesFile.write(line + "\n")

oldSeriesFile.close()
newSeriesFile.close()

print("Completed successfully!")



# Crop each image

print("Cropping images around centers...\n")

for i in range(sectionNum):
    
    if not centers[i] == (0, 0):
        
        # set up correct file name (there's probably a better way to do this)
        if i < 10:
            fileName = seriesName + "." + "00" + str(i) + ".tif"
        elif i < 100:
            fileName = seriesName + "." + "0" + str(i) + ".tif"
        elif i >= 100:
            fileName = seriesName + "." + str(i) + ".tif"

        print("Working on " + fileName + "...")
        
        # open original image with cv2 (PIL cannot handle large images)
        img = cv2.imread(oldLocation + "\\" + fileName)
        
        # get the cropping radius in pixels
        pixRad = rad * pixPerMic
        
        # get the center coordinates in pixels
        pixx = (centers[i][0] + domainOrigins[i][0]) * pixPerMic
        pixy = img.shape[0] - (centers[i][1] + domainOrigins[i][1]) * pixPerMic
        
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
        img.save(newLocation + "\\" + fileName)
        
        print("Saved!\n")

print("Cropping program has run succesfully!")



# Revert trace file domain origins to original values

input("WARNING: This will rewrite the trace files in this folder. Backing up your files is advised.\n" +
      "Press enter to continue.\n")

seriesName = input("What is the name of this series?: ")
sectionNum = int(input("What is the number of sections in this series? (make sure to include the 0 section): "))
croppedLocation = input("What is the file path for the folder with the cropped trace files?: ")

# check if user has domain origin data
hasData = ""
while hasData != "y" and hasData != "n":
    hasData = input("Do you have the ORIGINAL_DOMAIN_ORIGINS.txt file? (y/n): ")

# if user does have data...
if hasData == "y":

    #open text file
    originalOriginsFile = open(croppedLocation + "\\ORIGINAL_DOMAIN_ORIGINS.TXT")

    # read data from text file into list
    domainOrigins = []
    for line in originalOriginsFile.readlines():
        coords = line.split()
        domainOrigins.append([float(coords[0]), float(coords[1])])

    # close test file
    originalOriginsFile.close()

# if user does not have data, get it from the original trace files
elif hasData == "n":

    oldLocation = input("What is the file path for the uncropped series?: ")

    print("\nIdentifying domain origins...")

    # gather domain origins from trace files
    domainOrigins = []
    for i in range(sectionNum):
        domainOrigins.append(getDomainOrigin(oldLocation + '\\' + seriesName + "." + str(i)))

print("\nRestoring trace files to original domain...")

# rewrite domain origins
for i in range(sectionNum):
        restoreDomainOrigin(croppedLocation + '\\' + seriesName + "." + str(i),
                            domainOrigins[i][0], domainOrigins[i][1])

print("\nCompleted successfully!")
input("\nPress enter to exit")
