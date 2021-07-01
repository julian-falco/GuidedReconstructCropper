# Revert trace file domain origins to original values

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

# catch and display exceptions
try:
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

except Exception as e:
    print("ERROR: " + str(e))
