import os
import json
from PIL import Image as PILImage
PILImage.MAX_IMAGE_PIXELS = None
from pyrecon.utils.explore_files import findFiles
from pyrecon.utils.get_input import intInput, floatInput, ynInput
from pyrecon.utils.text_files import getBlankSection, getBlankSeries

def newChunkCrop(series_name, image_files, xchunks, ychunks, overlap, start_section, section_thickness, mic_per_pix, progbar=None):
    """Create a chunked series WITHOUT existing series or section files.
    """
    # create each folder
    os.mkdir("Cropped Images")
    for x in range(xchunks):
        for y in range(ychunks):
            os.mkdir("Cropped Images/" + str(x) + "," + str(y))

    # store new domain origins
    newDomainOrigins = []

    # create new tform_data file
    tform_data = {}
    tform_data["GLOBAL"] = {}

    # store max image length and height
    img_lengths = {}
    img_heights = {}

    # start iterating through each of the images
    if progbar:
        final_value = len(image_files)
        prog_value = 0
    for i in range(len(image_files)):
        # update progress
        if progbar:
            progbar.update_bar(prog_value/final_value * 100)
            prog_value += 1

        file_path = image_files[i]
        file_name = file_path[file_path.rfind("/")+1:]

        print("\nWorking on " + file_name + "...")

        # add data to GLOBAL tform_data and set focus to GLOBAL
        section_name = series_name + "." + str(i + start_section)
        tform_data["GLOBAL"][section_name] = {}
        tform_data["GLOBAL"][section_name]["src"] = file_name
        tform_data["GLOBAL"][section_name]["xcoef"] = [0,1,0,0,0,0]
        tform_data["GLOBAL"][section_name]["ycoef"] = [0,0,1,0,0,0]
        tform_data["FOCUS"] = "GLOBAL"

        # open image and get dimensions
        img = PILImage.open(file_path)
        img_length, img_height = img.size
        img_lengths[section_name] = img_length
        img_heights[section_name] = img_height
        
        # iterate through each chunk and calculate the coords for each of the corners
        for x in range(xchunks):
            newDomainOrigins.append([])
            for y in range(ychunks):
                
                left = int((img_length-1) * x / xchunks - overlap/2 / mic_per_pix)
                if left < 0:
                    left = 0
                right = int((img_length-1) * (x+1) / xchunks + overlap/2 / mic_per_pix)
                if right >= img_length:
                    right = img_length - 1
                
                top = int((img_height-1) * (ychunks - y-1) / ychunks - overlap/2 / mic_per_pix)
                if top < 0:
                        top = 0 
                bottom = int((img_height-1) * (ychunks - y) / ychunks + overlap/2 / mic_per_pix)
                if bottom >= img_height:
                    bottom = img_height - 1

                # crop the photo
                cropped = img.crop((left, top, right, bottom))
                
                newDomainOrigins[x].append((left, int(img_height-1 - bottom)))
                xshift_pix = left
                yshift_pix = int(img_height-1 - bottom)

                # save as uncompressed TIF
                image_path = "Cropped Images/" + str(x) + "," + str(y) + "/" + file_name
                cropped.save(image_path)

                # store data in tform_data file
                if i == 0:
                    tform_data["LOCAL_" + str(x) + "," + str(y)] = {}
                tform_data["LOCAL_" + str(x) + "," + str(y)][section_name] = {}
                tform_data["LOCAL_" + str(x) + "," + str(y)][section_name]["xshift_pix"] = xshift_pix
                tform_data["LOCAL_" + str(x) + "," + str(y)][section_name]["yshift_pix"] = yshift_pix
                tform_data["LOCAL_" + str(x) + "," + str(y)][section_name]["xcoef"] = [0,1,0,0,0,0]
                tform_data["LOCAL_" + str(x) + "," + str(y)][section_name]["ycoef"] = [0,0,1,0,0,0]
                tform_data["LOCAL_" + str(x) + "," + str(y)][section_name]["src"] = image_path

    # store tform_data in JSON file
    new_data = open(series_name + "_data.json", "w")
    json.dump(tform_data, new_data)
    new_data.close()

    # replace the unknowns in the section file with known info
    blank_section_txt = getBlankSection()
    blank_section_txt = blank_section_txt.replace("[SECTION_THICKNESS]", str(section_thickness))
    blank_section_txt = blank_section_txt.replace("[TRANSFORM_DIM]", "3")
    blank_section_txt = blank_section_txt.replace("[IMAGE_MAG]", str(mic_per_pix))

    # iterate through each section and create the section file
    for i in range(len(image_files)):

        file_path = image_files[i]
        file_name = file_path[file_path.rfind("/")+1:]

        section_name = series_name + "." + str(i + start_section)        
        newSectionFile = open(section_name, "w")

        # retrieve global transformations
        xcoef_list = tform_data["GLOBAL"][section_name]["xcoef"]
        ycoef_list = tform_data["GLOBAL"][section_name]["ycoef"]
        xcoef_str = str(xcoef_list).replace("[","").replace("]","").replace(",","")
        ycoef_str = str(ycoef_list).replace("[","").replace("]","").replace(",","")
    
        # replace section-specific unknowns with known info
        section_file_text = blank_section_txt.replace("[SECTION_INDEX]", str(i + start_section))
        section_file_text = section_file_text.replace("[IMAGE_SOURCE]", file_name)
        section_file_text = section_file_text.replace("[XCOEF]", xcoef_str)
        section_file_text = section_file_text.replace("[YCOEF]", ycoef_str)
        section_file_text = section_file_text.replace("[IMAGE_LENGTH]", str(int(img_lengths[section_name])))
        section_file_text = section_file_text.replace("[IMAGE_HEIGHT]", str(int(img_heights[section_name])))

        newSectionFile.write(section_file_text)
        newSectionFile.close()

    # create the series file
    blank_series_txt = getBlankSeries()
    blank_series_txt = blank_series_txt.replace("[SECTION_NUM]", str(start_section))

    new_series_file = open(series_name + ".ser", "w")
    new_series_file.write(blank_series_txt)
    new_series_file.close()

def chunkCrop(series, tform_data, images_dict, xchunks, ychunks, overlap, progbar=None):
    """Create a chunked series WITH existing series or section files.
    """

    # create each folder
    if not os.path.isdir("Cropped Images"):
        os.mkdir("Cropped Images")
    for x in range(xchunks):
        for y in range(ychunks):
            os.mkdir("Cropped Images/" + str(x) + "," + str(y))
    
    img_lengths = {}
    img_heights = {}

    # start iterating through each section
    if progbar:
        final_value = len(series.sections)
        prog_value = 0
    first_section = True
    for section_num in series.sections:
        if progbar:
            progbar.update_bar(prog_value/final_value * 100)
            prog_value += 1
        section = series.sections[section_num]
        file_path = images_dict[section.name]
        file_name = file_path[file_path.rfind("/")+1:]

        print("\nWorking on " + file_name + "...")

        # open image and get dimensions
        img = PILImage.open(file_path)
        img_length, img_height = img.size
        img_lengths[section.name] = img_length
        img_heights[section.name] = img_height
        mic_per_pix = section.images[0].mag
        
        # iterate through each chunk and calculate the coords for each of the corners
        for x in range(xchunks):
            for y in range(ychunks):
                
                left = int((img_length-1) * x / xchunks - overlap/2 / mic_per_pix)
                if left < 0:
                    left = 0
                right = int((img_length-1) * (x+1) / xchunks + overlap/2 / mic_per_pix)
                if right >= img_length:
                    right = img_length - 1
                
                top = int((img_height-1) * (ychunks - y-1) / ychunks - overlap/2 / mic_per_pix)
                if top < 0:
                        top = 0 
                bottom = int((img_height-1) * (ychunks - y) / ychunks + overlap/2 / mic_per_pix)
                if bottom >= img_height:
                    bottom = img_height - 1

                # crop the photo
                cropped = img.crop((left, top, right, bottom))
                xshift_pix = left
                yshift_pix = int(img_height-1 - bottom)

                # save as uncompressed TIF
                image_path = "Cropped Images/" + str(x) + "," + str(y) + "/" + file_name
                cropped.save(image_path)

                # store data in tform_data file
                if first_section:
                    tform_data["LOCAL_" + str(x) + "," + str(y)] = {}
                tform_data["LOCAL_" + str(x) + "," + str(y)][section.name] = {}
                tform_data["LOCAL_" + str(x) + "," + str(y)][section.name]["xshift_pix"] = xshift_pix
                tform_data["LOCAL_" + str(x) + "," + str(y)][section.name]["yshift_pix"] = yshift_pix
                tform_data["LOCAL_" + str(x) + "," + str(y)][section.name]["xcoef"] = [0,1,0,0,0,0]
                tform_data["LOCAL_" + str(x) + "," + str(y)][section.name]["ycoef"] = [0,0,1,0,0,0]
                tform_data["LOCAL_" + str(x) + "," + str(y)][section.name]["src"] = image_path
                
        first_section = False