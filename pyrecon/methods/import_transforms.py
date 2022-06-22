import numpy as np
from pyrecon.classes.transform import Transform
from pyrecon.utils.get_input import ynInput, intInput
from pyrecon.utils.explore_files import findFile

def changeGlobalTransformations(series, tform_data):
    """Change the global transformation of a series based on a .dat file
    """

    input("\nPress enter to select the file containing the transformations.")
    
    # open file explorer for user to select files
    new_tform_file = findFile("Data File", "dat")

    is_from_SWIFT = ynInput("\nIs this from SWIFT output? (y/n): ")

    if not is_from_SWIFT:
        print("\nEach line in the trasnformation file should contain the following information:")
        print("[line index] [six numbers indicating transformation applied to picture]")
        print("\nFor example:")
        print("0 1 0 0 0 1 0")
        print("1 1.13 0.1 0.53 0 0.9 0.6")
        print("2 1.11 0 0.51 0.01 0.92 0.9")
        print("...")
        print("\nPlease ensure that your file fits this format.")
        input("\nPress enter to continue.")

    # get number of lines in file
    new_file = open(new_tform_file, "r")
    num_lines = len(new_file.readlines())
    new_file.close()

    # pair line index with section nums
    idx_to_num = {}
    sec_nums = sorted(list(series.sections.keys()))
    if num_lines == len(series.sections):
        for i in range(num_lines):
            idx_to_num[i] = sec_nums[i]
    else:
        start_sec = intInput("What section number do the transformations start on?: ")
        start_idx = sec_nums.index(start_sec)
        for i in range(num_lines):
            idx_to_num[i] = sec_nums[i + start_idx]
    
    # ask user to keep or reset local transformations
    reset_local = ynInput("\nWould you like to reset your local transformations? (y/n): ")

    print("\nRetrieving transformations...")

    # get list of magnifications and image heights
    all_mags = []
    all_img_heights = []
    for i in range(num_lines):
        section_num = idx_to_num[i]
        mag = series.sections[section_num].images[0].mag
        all_mags.append(mag)
        img_height = series.sections[section_num].images[0].points[3][1] + 1
        all_img_heights.append(img_height)
    
    # get list of transformations
    all_tforms = getNewTransformations(new_tform_file, all_mags, is_from_SWIFT, all_img_heights)

    # go through each section and get the change transformation
    print("Applying transformations...")
    for i in range(num_lines):
        section = series.sections[idx_to_num[i]]
        current_global_xcoef = tform_data["GLOBAL"][section.name]["xcoef"]
        current_global_ycoef = tform_data["GLOBAL"][section.name]["ycoef"]
        current_global_tform = Transform(xcoef=current_global_xcoef, ycoef=current_global_ycoef)
        new_global_tform = all_tforms[i]

        # get the difference between the current and new transform (Dtform)
        change = current_global_tform.invert().compose(new_global_tform)

        # transform all of the traces AND the domain by the change transformation
        section.transformAllContours(change)
        section.transformAllImages(change)

        # update JSON GLOBAL tform_data
        new_xcoef = section.images[0].transform.xcoef
        new_ycoef = section.images[0].transform.ycoef
        tform_data["GLOBAL"][section.name]["xcoef"] = new_xcoef
        tform_data["GLOBAL"][section.name]["ycoef"] = new_ycoef

        # change local transformations as requested
        for crop in tform_data:
            if "LOCAL_" in crop:
                if reset_local:
                    # reset local transformations in JSON
                    tform_data[crop][section.name]["xcoef"] = [0,1,0,0,0,0]
                    tform_data[crop][section.name]["ycoef"] = [0,0,1,0,0,0]
                else:
                    # undo new transformation on local crops to preserve transformation
                    local_xcoef = tform_data[crop][section.name]["xcoef"]
                    local_ycoef = tform_data[crop][section.name]["ycoef"]
                    local_Dtform = Transform(xcoef=local_xcoef, ycoef=local_ycoef)
                    new_local_Dtform = change.invert().compose(local_Dtform)
                    # update local transformations in JSON file
                    tform_data[crop][section.name]["xcoef"] = new_local_Dtform.xcoef
                    tform_data[crop][section.name]["ycoef"] = new_local_Dtform.ycoef
        
    print("Success!")        

def getNewTransformations(new_tforms_file, mag_list, is_from_SWIFT=False, img_height_list=[]):
    """Returns all of the transformation matrices from a .dat file as a list of Transform objects.
    """
    # store file information
    new_tforms = open(new_tforms_file, "r")
    lines = new_tforms.readlines()
    new_tforms.close()
    
    all_transformations = []

    # iterate through each line (or section)
    for i in range(len(lines)):
        line = lines[i]

        # get info from line
        split_line = line.split()
        matrix_line = [float(num) for num in split_line[1:7]]
        tform_matrix = [[matrix_line[0],matrix_line[1],matrix_line[2]],
                       [matrix_line[3],matrix_line[4],matrix_line[5]],
                       [0,0,1]]
        
        if is_from_SWIFT:
            tform_matrix = matrix2recon(tform_matrix, img_height_list[i])
        
        # apply magnification
        tform_matrix[0][2] *= mag_list[i]
        tform_matrix[1][2] *= mag_list[i]

        # create Transform object
        a = np.linalg.inv(np.array(tform_matrix))
        xcoef = [a[0,2], a[0,0], a[0,1], 0, 0, 0]
        ycoef = [a[1,2], a[1,0], a[1,1], 0, 0, 0]
        tform = Transform(xcoef=xcoef, ycoef=ycoef)

        all_transformations.append(tform)

    return all_transformations


### MICHAEL CHIRILLO'S FUNCTION ###
def matrix2recon(transform, dim):
    """Change frame of reference for SWiFT transforms to work in Reconstruct.
    """
    new_transform = transform.copy()

    # Calculate bottom left corner translation
    BL_corner = np.array([[0], [dim], [1]])  # BL corner from image height in px
    BL_translation = np.matmul(transform, BL_corner) - BL_corner

    # Add BL corner translation to SWiFT matrix
    new_transform[0][2] = round(BL_translation[0][0], 5)  # x translation
    new_transform[1][2] = round(BL_translation[1][0], 5)  # y translation

    # Flip y axis - change signs a2, b1, and b3
    new_transform[0][1] *= -1  # a2
    new_transform[1][0] *= -1  # b1
    new_transform[1][2] *= -1  # b3

    # Stop-gap measure for Reconchonky
    new_transform = np.linalg.inv(new_transform)

    return new_transform