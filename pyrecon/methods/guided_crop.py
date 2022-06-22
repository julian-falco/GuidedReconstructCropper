import os
from pyrecon.utils.explore_files import findFiles
from pyrecon.utils.get_input import floatInput
from PIL import Image as PILImage
PILImage.MAX_IMAGE_PIXELS = None

def findBounds(series, obj_name):
    """Finds the bounds of a specified object on a single section file.
    """
    all_bounds = {}
    for section_num in series.sections:
        section = series.sections[section_num]
        # obtain list of all contours with obj_name
        all_contours = []
        for contour in section.contours:
            if contour.name == obj_name:
                all_contours.append(contour)
        # return None if contour not found in section
        if len(all_contours) == 0:
            all_bounds[section.name] = None
        else:
            # compile all transformed points
            all_points = []
            for contour in all_contours:
                fixed_points = contour.transform.transformPoints(contour.points)
                for point in fixed_points:
                    all_points.append(point)
            # get the domain transformation and inverse transformation
            domain_tform = section.images[0].transform # ASSUMES A SINGLE DOMAIN IMAGE
            domain_itform = domain_tform.inverse
            # compile points transformed by domain inverse transformation (ditform)
            all_points_ditform = domain_itform.transformPoints(all_points)
            x_vals = []
            y_vals = []
            for point in all_points_ditform:
                x_vals.append(point[0])
                y_vals.append(point[1])
            # get min and max values from points transformed by ditform
            x_min_ditform = min(x_vals)
            y_min_ditform = min(y_vals)
            x_max_ditform = max(x_vals)
            y_max_ditform = max(y_vals)
            # undo ditform
            bounds = domain_tform.transformPoints([(x_min_ditform, y_min_ditform), (x_max_ditform, y_max_ditform)])
            xmin = bounds[0][0]
            xmax = bounds[1][0]
            ymin = bounds[0][1]
            ymax = bounds[1][1]
            # return bounds fixed to Reconstruct space
            all_bounds[section.name] = (xmin, xmax, ymin, ymax)
    # fill in bounds data on sections where the object doesn't exist
    # if the first section(s) do not have the object, then fill it in with first object instance
    prev_bounds = None
    obj_found = False
    for bounds in all_bounds:
        if all_bounds[bounds] != None:
            prev_bounds = all_bounds[bounds]
            obj_found = True
            break
    # return None if obj was not found in entire series
    if not obj_found:
        return None
    # set any bounds points that are None to the previous bounds
    for bounds in all_bounds:
        if all_bounds[bounds] == None:
            all_bounds[bounds] = prev_bounds
        prev_bounds = all_bounds[bounds]
    # return bounds dictionary
    return all_bounds

def guidedCrop(series, obj_name, tform_data, images_dict, rad, progbar=None):
    """ Create a crop around an object.
    ENSURE THAT CROP FOCUS IS ALREADY SET TO GLOBAL BEFORE CALLING THIS FUNCTION.
    """
    # find the bounds for the object on each section
    bounds_dict = findBounds(series, obj_name)

    # check if trace was found in the series
    if not bounds_dict:
        raise Exception("This trace does not exist in this series.")
    
    # create the folder for the cropped images
    if not os.path.isdir("Cropped Images"):
        os.mkdir("Cropped Images")
    new_dir = "Cropped Images/" + obj_name
    os.mkdir(new_dir)

    # set up the tform_data file
    tform_data["LOCAL_" + obj_name] = {}

    # iterat through all section files
    if progbar:
        final_value = len(series.sections)
        prog_value = 0
    for section_num in series.sections:
        if progbar:
            progbar.update_bar(prog_value/final_value * 100)
            prog_value += 1
        section = series.sections[section_num]

        # set up the tform_data file
        tform_data["LOCAL_" + obj_name][section.name] = {}

        # fix the coordinates to the picture
        global_tform = section.images[0].transform
        xmin, xmax, ymin, ymax = bounds_dict[section.name]
        min_max_coords = global_tform.inverse.transformPoints([(xmin, ymin), (xmax, ymax)])
        # translate coordinates to pixels
        pix_per_mic = 1.0 / section.images[0].mag # get image magnification
        xshift_pix = int((min_max_coords[0][0] - rad) * pix_per_mic)
        if xshift_pix < 0:
            xshift_pix = 0
        yshift_pix = int((min_max_coords[0][1] - rad) * pix_per_mic)
        if yshift_pix < 0:
            yshift_pix = 0

        # write the shifted origin to the tform_data file
        tform_data["LOCAL_" + obj_name][section.name]["xshift_pix"] = xshift_pix
        tform_data["LOCAL_" + obj_name][section.name]["yshift_pix"] = yshift_pix
        # write identity transformation as Delta transformation
        tform_data["LOCAL_" + obj_name][section.name]["xcoef"] = [0,1,0,0,0,0]
        tform_data["LOCAL_" + obj_name][section.name]["ycoef"] = [0,0,1,0,0,0]

        # get the name/path of the desired image file from dictionary
        file_path = images_dict[section.name]
        file_name = file_path[file_path.rfind("/")+1:]
        print("\nWorking on " + file_name + "...")
        
        # open original image
        img = PILImage.open(file_path)

        # get image dimensions
        img_length, img_height = img.size

        # get the pixel coordinates for each corner of the crop
        left = int((min_max_coords[0][0] - rad) * pix_per_mic)
        bottom = img_height - int((min_max_coords[0][1] - rad) * pix_per_mic)
        right = int((min_max_coords[1][0] + rad) * pix_per_mic)
        top = img_height - int((min_max_coords[1][1] + rad) * pix_per_mic)
        
        # if crop exceeds image boundary, cut it off
        if left < 0: left = 0
        if right >= img_length: right = img_length-1
        if top < 0: top = 0
        if bottom >= img_height: bottom = img_height-1

        # crop the photo
        cropped_src = new_dir + "/" + file_name
        cropped = img.crop((left, top, right, bottom))
        cropped.save(cropped_src)
        # store the local src for the image in tform_data
        tform_data["LOCAL_" + obj_name][section.name]["src"] = cropped_src