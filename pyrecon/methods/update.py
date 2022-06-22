import os
import json
from pyrecon.utils import reconstruct_writer as rw
from pyrecon.utils import reconstruct_reader as rr

def newJSON(series):
    """ Create a new JSON file for an existing uncropped series.
    """
    tform_data = {}
    tform_data["GLOBAL"] = {}
    tform_data["FOCUS"] = "GLOBAL"
    for section_num in series.sections:
        section = series.sections[section_num]
        tform_data["GLOBAL"][section.name] = {}
        tform_data["GLOBAL"][section.name]["xcoef"] = section.images[0].transform.xcoef
        tform_data["GLOBAL"][section.name]["ycoef"] = section.images[0].transform.ycoef
        tform_data["GLOBAL"][section.name]["src"] = section.images[0].src
    with open(series.name + "_data.json", "w") as new_file:
        json.dump(tform_data, new_file)
    return tform_data

def readAll(series_dir, progbar=None):
    """ Import series and tform data.
    """
    series = rr.process_series_directory(series_dir, progbar=progbar)
    if not os.path.isfile(series.name + "_data.json"):
        tform_data = newJSON(series)
    else:
        with open(series.name + "_data.json", "r") as data_file:
            tform_data = json.load(data_file)
    return series, tform_data

def readJSON(series_name):
    with open(series_name + "_data.json", "r") as data_file:
        tform_data = json.load(data_file)
    return tform_data


def writeAll(series, tform_data, progbar=None):
    """ Export series and tform data to saved files.
    """
    directory = os.getcwd()
    rw.write_series(series, directory, sections=True, overwrite=True, progbar=progbar)
    with open(series.name + "_data.json", "w") as new_file:
        json.dump(tform_data, new_file)
    new_file.close()