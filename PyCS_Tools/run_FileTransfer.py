"""

        File Transfer System.
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
from PyCS_System.text_utils import option_menu
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
    ### Starting the argparser ###
    parser = argparse.ArgumentParser() # setting up the command line argument parser
    parser.add_argument("-o","--output_type",type=str,default="FILE",help="The type of output to use for logging.")
    parser.add_argument("-l","--logging_level",type=int,default=10,help="The level of logging to use.")

    args = parser.parse_args()

    ### Setting up logging ###
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    log_print("Running run_RAMSES.py.", _dbg_string, "debug")
    time.sleep(0.1)
    ### Setting up the run ###
    upload_download_choice = option_menu(["Download to Local","Upload to Box"],desc={"Download to Local":"Download a file from box.",
                                                                                     "Upload to Box":"Send a file to box from local drive."},
                                         title="File Transfer System")
    print(upload_download_choice)
    if upload_download_choice == "Download to Local":
        ### We are downloading
        download_files(threaded=CONFIG["system"]["multiprocessing"]["threaded"])
    else:
        upload_files(threaded=CONFIG["system"]["multiprocessing"]["threaded"])