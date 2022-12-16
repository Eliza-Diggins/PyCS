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
from PyCS_System.text_utils import get_options,set_simulation_information
import time
from PyCS_System.SimulationMangement import add_simulation
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
    #Parsing Arguments
########################################################################################################################
    parser = argparse.ArgumentParser() # setting up the command line argument parser
    parser.add_argument("-o","--output_type",type=str,default="FILE",help="The type of output to use for logging.")
    parser.add_argument("-l","--logging_level",type=int,default=10,help="The level of logging to use.")

    args = parser.parse_args()

    #Setup Tasks
########################################################################################################################
    set_log(_filename,output_type=args.output_type,level=args.logging_level)
    log_print("Running run_RAMSES.py.",_dbg_string,"debug")
    time.sleep(0.1)

    ### Setting up the run ###
    print_title("run_RAMSES 1.0","Eliza Diggins")

    #Grabbing data
########################################################################################################################
    selected_ic_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                   lambda file: ".dat" in file or ".g2" in file,
                                   search_for_description=False)
    selected_ic_path = os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],selected_ic_file)
    log_print("Running RAMSES with initial conditions file %s."%selected_ic_path,_dbg_string,"debug")

    #Generating NML data
########################################################################################################################
    ramses_configuration_data = read_RAMSES_config() # reading the RAMSES config.

    # changing defaults to reflect choice of IC file.
    init_file,ic_file = list(ramses_configuration_data["INIT_PARAMS"]["initfile(1)"][0]),list(ramses_configuration_data["DICE_PARAMS"]["ic_file"][0])
    init_file[0],ic_file[0] = "'%s'"%CONFIG["system"]["directories"]["initial_conditions_directory"],"'%s'"%selected_ic_file
    ramses_configuration_data["INIT_PARAMS"]["initfile(1)"] = tuple(init_file)
    ramses_configuration_data["DICE_PARAMS"]["ic_file"] = tuple(ic_file)

    # grabbing proper settings #
    time.sleep(0.1) # just waiting for prints to finish.
    ramses_config = get_options(ramses_configuration_data,"RAMSES Configuration")
    time.sleep(0.1)

    #Generating simulation settings
########################################################################################################################

    # getting user input for simulation #
    sim_data = set_simulation_information()

    ### Auto-generating data if not provided.
    # Setting simulation name #
    if sim_data['SimulationName']=="None":
        sim_data["SimulationName"] = "Simulation_"+datetime.now().strftime('%m-%d-%Y_H%H')

    # Setting the simulation description
    if sim_data['Description'] == "None":
        sim_data["Description"] = "RAMSES simulation run at %s."%datetime.now().strftime('%m-%d-%Y_%H-%M-%S')

    if sim_data["NMLFile"] == "None":
        # grab the names of the nml files that already exist
        nml_names = [file for file in os.listdir(CONFIG["system"]["directories"]["RAMSES_nml_directory"]) if ".nml" in file]
        try:
            name = ramses_config["DICE_PARAMS"]["ic_file"][0].split(".")[0][1:] + ".nml"

        except KeyError:
            name = "RAMSES_nml.nml"

        name_already_exists = name in nml_names
        l = 0
        base_name = name
        while name_already_exists:  # we need to keep fixing up the name until we find something logically reasonable.
            name = base_name.split(".")[0] + "_(%s)" % l + ".nml"
            name_already_exists = name in nml_names
            l += 1
        sim_data["NMLFile"] = os.path.join(CONFIG["system"]["directories"]["RAMSES_nml_directory"],name)
    else:
        name = sim_data["NMLFile"]

   ### Providing additional data ###
    sim_data["ICFile"] = selected_ic_file # grab the IC file path
    sim_data["SLURMDate"] = datetime.now()
    sim_data["SimulationLocation"]=os.path.join(ramses_output_file,sim_data["SimulationName"])
    sim_data["NMLFile"] = os.path.join(CONFIG["system"]["directories"]["RAMSES_nml_directory"],name)

    ### Generating the sim
    add_simulation(**sim_data)

    # Generating the SLURM File
########################################################################################################################


    # writing the .nml file.
    nml_path = write_nml(ramses_config,name=name) # We found the nml path.

    time.sleep(0.1)
    ### Creating the batch script ###
    slurm_name = input("%s[Input] Select a name for the .slurm file. [return to auto-generate]:"%_dbg_string)
    if slurm_name == "":
        slurm_name = "SLURM_RAMSES_%s.slurm"%sim_data["SimulationName"]

    # generating output file #
    if not os.path.exists(sim_data["SimulationLocation"]):
        pt.Path.mkdir(pt.Path(sim_data["SimulationLocation"]),parents=True)

    command_string = command_string%(sim_data["SimulationLocation"],
                                     ramses_exec,
                                     nml_path)
    time.sleep(0.1)
    write_slurm_script(command_string,
                       name=slurm_name,
                       type="RAMSES",
                       description=sim_data["Description"],
                       batch=True)

