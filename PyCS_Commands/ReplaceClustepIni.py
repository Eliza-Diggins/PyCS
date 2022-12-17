"""

        Run_Clustep script
        Eliza Diggins

"""
import os
import sys
import pathlib as pt

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_System.text_utils import print_title,set_simulation_information
from PyCS_System.SpecConfigs import read_clustep_config,write_slurm_script,write_clustep_ini
import pathlib as pt
from datetime import datetime
from PyCS_System.text_utils import get_options
import time
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Commands"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# - Grabbing the clustep parameter file location.
clustep_ini_file = os.path.join(CONFIG["system"]["executables"]["CLUSTEP_install"],"params_cluster.ini")
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    #Argument Parsing
########################################################################################################################
    parser = argparse.ArgumentParser() # setting up the command line argument parser
    parser.add_argument("IniFile",type=str,help="The ini file to replace in the location. (Global path.)")
    parser.add_argument("-o","--output_type",type=str,default="FILE",help="The type of output to use for logging.")
    parser.add_argument("-l","--logging_level",type=int,default=10,help="The level of logging to use.")
    args = parser.parse_args()

    #Setup
########################################################################################################################
    set_log(_filename,output_type=args.output_type,level=args.logging_level)

    # MAIN
########################################################################################################################
    log_print("Replacing %s with %s."%(clustep_ini_file,args.IniFile),_dbg_string,"info")
    os.system("mv %s %s"%(args.IniFile,clustep_ini_file))
    log_print("Replaced %s with %s."%(clustep_ini_file,args.IniFile),_dbg_string,"info")
