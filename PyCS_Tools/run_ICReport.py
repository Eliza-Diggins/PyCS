"""

Grabs a report on a specified IC file.
    Written by: Eliza Diggins
"""
import sys
import pathlib as pt
import os
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
import pathlib as pt
import toml
from datetime import datetime
import pynbody as pyn
from PyCS_System.text_utils import file_select,print_title
from PyCS_System.file_management import upload_files,download_files
import time
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    #Argument Parsing
########################################################################################################################
    parser = argparse.ArgumentParser() # setting up the command line argument parser
    parser.add_argument("-o","--output_type",type=str,default="FILE",help="The type of output to use for logging.")
    parser.add_argument("-l","--logging_level",type=int,default=10,help="The level of logging to use.")
    #parser.add_argument("-nb","--no_batch",action="store_true",help="Use batch to run.") TODO: Is this worth it for versatility?
    args = parser.parse_args()

    #Setup
    ########################################################################################################################
    #- Logging -#
    set_log(_filename,output_type=args.output_type,level=args.logging_level)

    #- Making a title -#
    print_title("Initial Conditions Reports","Eliza Diggins")

    #- Dataset creation -#
    report_data = {"General":{}}

    # Selecting an IC file
    ####################################################################################################################
    initial_condition_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],conditions=lambda fn: any(i in fn for i in [".dat",".g2",".g1"]))

    # Opening the IC file and grabbing preliminary data
    ####################################################################################################################
    log_print("Attempting to open the selected file at %s."%os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],initial_condition_file),
              _dbg_string,"debug")

    #- Opening the file -#
    snapshot = pyn.load(os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],initial_condition_file))

    #- grabbing the preliminary interesting data -#
    report_data["General"]["N Particles"] = len(snapshot) # recording the total number of particles
    report_data["General"]["Families"] = [fam.name for fam in snapshot.families()]
    report_data["General"]["Loadable_keys"] = [key for key in snapshot.loadable_keys()]

    #- Giving family level general data -#
    for family in snapshot.families():
        report_data["General"][family.name] = {}
        report_data["General"][family.name]["N Particles"] = len(snapshot[family])
        report_data["General"][family.name]["Loadable_keys"] = [key for key in snapshot[family].loadable_keys()]

    print(report_data)

