# Revert trace file domain origins to original values

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
