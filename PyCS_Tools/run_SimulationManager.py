"""

        Simulation Manager for use on CHPC
        Written by: Eliza Diggins

"""
import os
import sys
import pathlib as pt

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_System.text_utils import file_select,print_title
from PyCS_System.SpecConfigs import read_RAMSES_config, read_batch_config, write_nml,write_slurm_script
import pathlib as pt
import PyCS_System.SimulationMangement as sim_manage
import toml
from datetime import datetime
from PyCS_System.text_utils import get_options,set_simulation_information
import time
from PyCS_System.SimulationMangement import add_simulation
from colorama import Fore, Back, Style
from sshkeyboard import listen_keyboard,stop_listening
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
__global_simulation_location = None # This holds direct data on where we are in the global namescape.
__global_update_check = True # We use this to know when to update the listing
__subcycle_check = 0
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def print_key(key):
    global simlog
    global __subcycle_check

    os.system('cls' if os.name == 'nt' else 'clear')
    print_title("Simulation Manager (Version %s)" % CONFIG["system"]["version"], "Written by: Eliza Diggins")
    for key,value in simlog[key].items():
        print("[%s] %s"%(Fore.GREEN+Style.BRIGHT+str(key)+Style.RESET_ALL,str(value)))


def on_press_main(key):
    """
    Key press function for the main cycle.
    Parameters
    ----------
    key

    Returns
    -------

    """
    # grabbing globals
    global __global_update_check
    global __global_simulation_location
    global __subcycle_check
    global simlog

    ## Managing key entering ##
    try:
        if __subcycle_check == 0:
            if key == "enter":
                # We need to enter the selected value
                stop_listening()
                __subcycle_check = 1
            elif key == "down":
                keys = list(simlog.keys())
                key_id = keys.index(__global_simulation_location)
                __global_simulation_location = (keys[key_id+1] if key_id != len(keys)-1 else keys[1])
                stop_listening()
            elif key == "up":
                keys = list(simlog.keys())
                key_id = keys.index(__global_simulation_location)
                __global_simulation_location = (keys[key_id - 1] if key_id != 1 else keys[-1])
                stop_listening()
        else:
            if key == "enter":
                # We need to enter the selected value
                stop_listening()
                __subcycle_check = 0
    except AttributeError as ex:
        print(ex)
        exit()

def on_press_sub(key):
    global __subcycle_check
    if key == "enter":
        __subcycle_check = True
        stop_listening()
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
    set_log(_filename,output_type=args.output_type,level=args.logging_level)

    # Loading static variables
########################################################################################################################
    simlog = sim_manage.read_simulation_log()
    # STARTING THE RUN CYCLE
########################################################################################################################
    exit_check = False # check variable for system exit.

    while not exit_check: # Main program cycle.
        if __global_simulation_location == None:
            __global_simulation_location = list(simlog.keys())[0]
        if __global_update_check: # We need to get calcs
            calcs = sim_manage.print_calcs(simlog)
            __global_update_check = False
        # Printing Title
    ####################################################################################################################
        print_title("Simulation Manager (Version %s)"%CONFIG["system"]["version"],"Written by: Eliza Diggins")

        if __subcycle_check == 0:
            sim_manage.print_simulation_log(calcs=calcs,simlog=simlog,location=__global_simulation_location)
        else:
            print_key(__global_simulation_location)
        # Keyboard listening
    ####################################################################################################################
        listen_keyboard(on_press=on_press_main)
        os.system('cls' if os.name == 'nt' else 'clear')