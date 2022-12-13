"""

        RUN RAMSES script
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
import toml
from datetime import datetime
from PyCS_System.text_utils import get_options
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
ramses_exec = CONFIG["system"]["executables"]["RAMSES_exec"]
ramses_output_file = CONFIG["system"]["directories"]["RAMSES_simulations_directory"]
command_string = """
#- Module Setup -#
ml purge
ml gcc/8.5.0
ml openmpi/4.1.3

#- Environment Management -#
setenv WORKDIR %s
cd $WORKDIR

#- Main Command -#
mpirun -np $SLURM_NTASKS %s %s
"""
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
    log_print("Running run_RAMSES.py.",_dbg_string,"debug")
    time.sleep(0.1)
    ### Setting up the run ###
    print_title("run_RAMSES 1.0","Eliza Diggins")

    ### Grabbing an initial conditions file ###
    selected_ic_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                   lambda file: ".dat" in file or ".g2" in file,
                                   search_for_description=False)
    selected_ic_path = os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],selected_ic_file)
    log_print("Running RAMSES with initial conditions file %s."%selected_ic_path,_dbg_string,"debug")

    ### Generating the RAMSES settings ###
    ramses_configuration_data = read_RAMSES_config() # reading the RAMSES config.

    # changing defaults to reflect choice of IC file.
    ramses_configuration_data["INIT_PARAMS"]["initfile(1)"] = "'%s'"%CONFIG["system"]["directories"]["initial_conditions_directory"]
    ramses_configuration_data["DICE_PARAMS"]["ic_file"]="'%s'"%selected_ic_file

    # grabbing proper settings #
    time.sleep(0.1) # just waiting for prints to finish.
    ramses_config = get_options(ramses_configuration_data,"RAMSES Configuration")
    time.sleep(0.1)
    # grabbing a name for the nml #
    name = input("%s[Input] Select a name for the .nml file. [return to auto-generate]:"%_dbg_string)
    if name == "":
        name = None

    # writing the .nml file.
    nml_path = write_nml(ramses_config,name=name) # We found the nml path.

    time.sleep(0.1)
    ### Creating the batch script ###
    slurm_name = input("%s[Input] Select a name for the .slurm file. [return to auto-generate]:"%_dbg_string)
    if slurm_name == "":
        slurm_name = None

    # generating output file #
    if not os.path.exists(os.path.join(ramses_output_file,selected_ic_file.split(".")[0])):
        pt.Path.mkdir(pt.Path(os.path.join(ramses_output_file,selected_ic_file.split(".")[0])),parents=True)

    command_string = command_string%(os.path.join(ramses_output_file,selected_ic_file.split(".")[0]),
                                     ramses_exec,
                                     nml_path)
    time.sleep(0.1)
    write_slurm_script(command_string,
                       name=slurm_name,
                       type="RAMSES",
                       description=input("%s[Input]: Please provide a description for the SLURM file:"%_dbg_string),
                       batch=True)

