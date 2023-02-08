"""
    RAyInit.py is designed to allow the use of RAMSES as a file type converter from gadget files to more suitable
    RAMSES grid outputs. These can then be run from the run_RAMSES.py file as normal.

"""
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_System.text_utils import file_select, print_title
from PyCS_System.SpecConfigs import read_RAMSES_config, write_nml, write_slurm_script
from PyCS_Tools.run_RAMSES import issue_memory_waring
import pathlib as pt
import numpy as np
import pynbody as pyn
from datetime import datetime
from PyCS_System.text_utils import get_options, set_simulation_information
import time
from PyCS_System.SimulationMangement import SimulationLog
from colorama import Fore, Style
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
simlog = SimulationLog.load_default()
# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# - Grabbing the correct executables -#
ramses_exec = CONFIG["system"]["executables"]["RAMSES_exec"]

# - Grabbing the data storage directories -#
raymond_output_file = CONFIG["system"]["directories"]["RAYMOND_simulations_directory"]

# - Writing the command string to pass to system for the run -#
command_string = """
#- Module Setup -#
ml purge
ml gcc/8.5.0
ml openmpi/4.1.3

#- Environment Management -#
setenv WORKDIR %s
cd $WORKDIR

#- Main Command -#
mpirun -np $SLURM_NTASKS '%s' '%s'
"""

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------- Sub-Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # Parsing Arguments
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")

    args = parser.parse_args()

    # Setup Tasks
    ########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    log_print("Running run_RAyInit.py.", _dbg_string, "debug")
    time.sleep(0.1)

    ### Setting up the run ###
    print_title("run_RAyInit %s" % CONFIG["system"]["version"], "Eliza Diggins")

    # Grabbing data
    ########################################################################################################################
    selected_ic_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                   lambda file: ".dat" in file or ".g2" in file,
                                   search_for_description=False)
    selected_ic_path = os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], selected_ic_file)
    os.system('cls' if os.name == 'nt' else 'clear')
    log_print("Running RAyInit with initial conditions file %s." % selected_ic_path, _dbg_string, "debug")

    # Generating NML data
    ########################################################################################################################
    ramses_configuration_data = read_RAMSES_config()  # reading the RAMSES config.

    # changing defaults to reflect choice of IC file.
    default_temp = list(ramses_configuration_data["CORE"]["ic_file"])  # grab the default tuple
    default_temp[0] = "'%s'" % selected_ic_path  # setting the IC path
    ramses_configuration_data["CORE"]["ic_file"] = tuple(default_temp)  # adding back to settings.

    # grabbing proper settings #
    time.sleep(0.1)  # just waiting for prints to finish.

    # Cleaning standard RAMSES nml File to remove superfluous options
    # -----------------------------------------------------------------------------------------------------------------#
    ramses_configuration_data = {key: value for key, value in ramses_configuration_data.items() if
                                 key in ["CORE","RUN_PARAMS", "AMR_PARAMS", "REFINE_PARAMS"]}
    ramses_config = get_options(ramses_configuration_data, "RAMSES Configuration")

    # - Recombining with the necessary backbones -#
    ramses_config = {(key): (ramses_config[key] if key in ramses_config else value) for key, value in
                     read_RAMSES_config().items() if
                     key not in ["MOVIE_PARAMS", "COOLING_PARAMS", "SF_PARAMS", "FEEDBACK_PARAMS", "MOND_PARAMS"]}

    # - Setting necessary values -#
    #  We hard set the output parameters because we only want to generate the initial condition. We force
    #  run times less than 1 hour by fixing the walltime max to 1 hr.
    #
    ramses_config["OUTPUT_PARAMS"] = {
        "noutput":["1","1","Number of outputs"],
        "tout":["0.0,","0.0,","The times of outputs"],
        "walltime_hrs":["1.","1.","Walltime"],
        "minutes_dump":["10","10",""]
    }

    time.sleep(0.1)
    os.system('cls' if os.name == 'nt' else 'clear')

    #------------------------------------------------------------------------------------------------------------------#
    # GENERATING THE SIMULATION SETTINGS FOR LOGGING
    #------------------------------------------------------------------------------------------------------------------#
    # getting user input for simulation #
    sim_data = set_simulation_information() #-> Grabs the user's input about NML, Name, and description.

    os.system('cls' if os.name == 'nt' else 'clear')

    ### Auto-generating data if not provided.
    # Setting simulation name #
    if sim_data['SimulationName'] == "None":
        sim_data["SimulationName"] = "Simulation_" + datetime.now().strftime('%m-%d-%Y_H%H')

    # Setting the simulation description
    if sim_data['Description'] == "None":
        sim_data["Description"] = "RayInit simulation run at %s." % (datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))


    ### Providing additional data ###
    sim_data["ICFile"] = selected_ic_file  # grab the IC file path
    sim_data["SLURMDate"] = "None"
    sim_data["Software"] = "None"
    sim_data["NMLFile"] = "None"

    # - setting the output location -#
    sim_data["SimulationLocation"] = os.path.join(raymond_output_file, sim_data["SimulationName"])

    ### Generating the sim
    simlog.append(sim_data)

    ##- Grabbing the matching simulation log id -##
    simlog_key = simlog._keys_from_name(sim_data["SimulationName"])[0]

    # Issuing the memory warning
    ####################################################################################################################
    issue_memory_waring(ramses_config)

    # Generating the SLURM File
    ########################################################################################################################

    # writing the .nml file.
    nml_path = write_nml(ramses_config,
                         name="RAyINIT_TEMP.nml",  # We found the nml path.
                         output_location=os.path.join(CONFIG["system"]["directories"]["temp_directory"],simlog_key))

    time.sleep(0.1)

    ### Creating the batch script ###
    slurm_name = input("%s[Input] Select a name for the .slurm file. [return to auto-generate]:" % _dbg_string)
    if slurm_name == "":
        slurm_name = "SLURM_%s_%s.slurm" % ("RAyInit", sim_data["SimulationName"])

    # generating output file #
    command_string = command_string % (sim_data["SimulationLocation"],
                                           ramses_exec,
                                           nml_path)

    time.sleep(0.1)
    os.system('cls' if os.name == 'nt' else 'clear')
    write_slurm_script(command_string,
                       name=slurm_name,
                       type=ramses_config["CORE"]["software"][0],
                       batch=True)
