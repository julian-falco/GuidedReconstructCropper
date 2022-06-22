from pyrecon.classes import Transform

def findRealignment(series, local_name, tform_data):
    """Check for and return differences in domain alignment between current local series and global series.
    """
    # store Delta transformations (Dtforms)
    Dtforms = {}
    for section_num in series.sections:
        section = series.sections[section_num]
        # get current current local transform, xshift, and yshift
        xshift_pix = tform_data["LOCAL_" + local_name][section.name]["xshift_pix"]
        yshift_pix = tform_data["LOCAL_" + local_name][section.name]["yshift_pix"]
        mag = section.images[0].mag
        translate = Transform.getTranslateTransform(xshift_pix * mag, yshift_pix * mag)
        # get local and global transforms
        local_tform = section.images[0].transform
        global_xcoef = tform_data["GLOBAL"][section.name]["xcoef"]
        global_ycoef = tform_data["GLOBAL"][section.name]["ycoef"]
        global_tform = Transform(xcoef=global_xcoef, ycoef=global_ycoef)
        # get the Dtform
        # Dtform = -(translate * global) * local
        Dtform = (translate * global_tform).inverse * local_tform
        # store in dictionary
        Dtforms[section.name] = Dtform, translate # also get translate so it is not recalculated later
    return Dtforms

def saveAsGlobal(series, tform_data):
    for section_num in series.sections:
        section = series.sections[section_num]
        tform_data["GLOBAL"][section.name]["xcoef"] = section.images[0].transform.xcoef
        tform_data["GLOBAL"][section.name]["ycoef"] = section.images[0].transform.ycoef
        tform_data["GLOBAL"][section.name]["src"] = section.images[0].src

def switchToGlobal(series, obj_name, tform_data, progbar=None):
    """Switch focus to the uncropped series from a cropped version.
    """
    # set up progress bar
    if progbar:
        final_value = len(series.sections)
        prog_value = 0
    # check for transformations that deviate from the global alignment
    Dtforms = findRealignment(series, obj_name, tform_data)
    for section_num in series.sections:
        # update progress bar
        if progbar:
            progbar.update_bar(prog_value/final_value * 100)
            prog_value += 1
        section = series.sections[section_num]
        Dtform, translate = Dtforms[section.name]        
        # store the new Delta transformation in tform_data
        tform_data["LOCAL_" + obj_name][section.name]["xcoef"] = Dtform.xcoef
        tform_data["LOCAL_" + obj_name][section.name]["ycoef"] = Dtform.ycoef
        # change the transformations
        # CONTOURS: global = local * -Dtform
        section.transformAllContours(Dtform.inverse)
        # IMAGES: global = -translate * (local + -Dtform)
        section.transformAllImages(Dtform.inverse)
        section.transformAllImages(translate.inverse, reverse=True)
        # change the image source
        section.images[0].src = tform_data["GLOBAL"][section.name]["src"]
        tform_data["FOCUS"] = "GLOBAL"

def switchToCrop(series, obj_name, tform_data, progbar):
    """Switch focus from an uncropped series to a cropped one.
    """    
    # save current alignment as global
    saveAsGlobal(series, tform_data)
    # set up progress bar
    if progbar:
        final_value = len(series.sections)
        prog_value = 0
    for section_num in series.sections:
        # add to progress bar
        if progbar:
            progbar.update_bar(prog_value/final_value * 100)
            prog_value += 1
        section = series.sections[section_num]
        Dtform_xcoef = tform_data["LOCAL_" + obj_name][section.name]["xcoef"]
        Dtform_ycoef = tform_data["LOCAL_" + obj_name][section.name]["ycoef"]
        Dtform = Transform(xcoef=Dtform_xcoef, ycoef=Dtform_ycoef)
        # get the translation coordinates
        xshift_pix = tform_data["LOCAL_" + obj_name][section.name]["xshift_pix"]
        yshift_pix = tform_data["LOCAL_" + obj_name][section.name]["yshift_pix"]
        mag = section.images[0].mag
        translate = Transform.getTranslateTransform(xshift_pix * mag, yshift_pix * mag)
        # CONTOURS: local = global + Dtform
        section.transformAllContours(Dtform)
        # IMAGES: local = (translate + global) + Dtform 
        section.transformAllImages(translate, reverse=True)
        section.transformAllImages(Dtform)
        # change the image source
        section.images[0].src = tform_data["LOCAL_" + obj_name][section.name]["src"]  
        tform_data["FOCUS"] = "LOCAL_" + obj_name
