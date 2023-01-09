"""

        RUN RAMSES script, with forward compatibility with RAYMOND
            Written by: Eliza Diggins
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
import pathlib as pt
import numpy as np
import pynbody as pyn
from datetime import datetime
from PyCS_System.text_utils import get_options, set_simulation_information
import time
from PyCS_System.SimulationMangement import add_simulation
from colorama import Fore, Style
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Tools"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
#- Grabbing the correct executables -#
ramses_exec = CONFIG["system"]["executables"]["RAMSES_exec"]
aqual_exec = CONFIG["system"]["executables"]["AQUAL_exec"]
qumond_exec = CONFIG["system"]["executables"]["AQUAL_exec"]

#- Grabbing the data storage directories -#
ramses_output_file = CONFIG["system"]["directories"]["RAMSES_simulations_directory"]
raymond_output_file = CONFIG["system"]["directories"]["RAYMOND_simulations_directory"]

#- Writing the command string to pass to system for the run -#
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
def issue_memory_waring(nml_config):
    """
    Issues a memory warning to the user regarding their choice of ngrid and npart.
    Parameters
    ----------
    nml_config: the nml config being used.

    Returns: None
    -------

    """
    # - grabbing the correct memory mode -#
    mem_mode = nml_config["CORE"]["Memory"]["mode"][0]
    ngrid, npart = nml_config["AMR_PARAMS"]["ngrid"][0], nml_config["AMR_PARAMS"]["npart"][0]
    box_size = (float(nml_config["AMR_PARAMS"]["boxlen"][0]) * float(
        nml_config["UNITS_PARAMS"]["units_length"][0])) * pyn.units.Unit("cm")
    levelmin, levelmax = int(nml_config["AMR_PARAMS"]["levelmin"][0]), int(nml_config["AMR_PARAMS"]["levelmax"][0])
    ##- converting to parsecs -##

    box_size = box_size.in_units("pc")

    # grabbing the ic location and length
    ic_loc = os.path.join(nml_config["INIT_PARAMS"]["initfile(1)"][0].replace("'", ""),
                          nml_config["DICE_PARAMS"]["ic_file"][0].replace("'", ""))

    snap = pyn.load(ic_loc)
    ic_parts = (len(snap.dm), len(snap.g))
    del snap

    # Producing computations
    ####################################################################################################################
    # - computing total memory requirement -#
    mem_val = 1.4 * (int(ngrid) / (10 ** 6)) + 0.7 * (int(npart) / (10 ** 7))
    if mem_mode == "tot":
        mem_val_string = "%s GB" % np.round(mem_val, decimals=2)
    else:
        mem_val_string = "%s GB/CPU (%s GB / 16 Core Node)" % (
        np.round(mem_val, decimals=2), np.round(mem_val * 16, decimals=2))

    # - Computing the resolution -#
    ngrids_min, ngrids_max = 2 ** (levelmin - 1), 2 ** (levelmax - 1)
    min_res, max_res = np.round(box_size / ngrids_min, decimals=5), np.round(box_size / ngrids_max, decimals=5)

    # - Computing the maximal resolvable level -#
    if mem_mode == "tot":
        max_lev = str(np.floor((np.log2(int(ngrid)) / 3) + 1))
    else:
        max_lev = str(np.floor((np.log2(int(ngrid)) / 3) + 1)) + "+(1/3)log2(cpus)"
    # Issuing the report
    ####################################################################################################################
    print_title("Memory Report", "")
    print("#" + ("-") * 24 + Fore.GREEN + Style.BRIGHT + "  General  " + Style.RESET_ALL + ("-") * 24 + "#")
    if mem_mode == "tot":
        # - General -#
        print("[%s] = %s\n[%s] = %s\t\t [%s] = %s" % (
            Fore.CYAN + Style.BRIGHT + "ngridtot" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ngrid) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "nparttot" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(npart) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Total Memory Required" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + mem_val_string + Style.RESET_ALL))

        # - Allocation -#
        print("#" + ("-") * 24 + Fore.GREEN + Style.BRIGHT + "  Allocation  " + Style.RESET_ALL + ("-") * 24 + "#")
        print("[%s] = %s (%s %% Usage)\n\t{Dark Matter: %s (%s %% Usage), Baryonic: %s (%s %% Usage)}" % (
            Fore.CYAN + Style.BRIGHT + "Total Particles" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(sum(list(ic_parts))) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(
                np.round(100 * sum(list(ic_parts)) / float(npart), decimals=3)) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ic_parts[0]) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.round(100 * ic_parts[0] / float(npart), decimals=3)) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ic_parts[1]) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.round(100 * ic_parts[1] / float(npart), decimals=3)) + Style.RESET_ALL,
        ))
        # - AMR Statistics -#
        print("#" + ("-") * 24 + Fore.GREEN + Style.BRIGHT + "  AMR Stats  " + Style.RESET_ALL + ("-") * 24 + "#")
        print("[%s] = %s" % (Fore.CYAN + Style.BRIGHT + "Box Size" + Style.RESET_ALL,
                             Fore.RED + Style.BRIGHT + str(np.round(box_size, decimals=3)) + " pc" + Style.RESET_ALL))
        print("[%s] = %s (%s: %s), [%s] = %s (%s: %s)" % (
            Fore.CYAN + Style.BRIGHT + "Min. Level" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(levelmin) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Res" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(min_res) + " pc" + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Max. Level" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(levelmax) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Res" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(max_res) + " pc" + Style.RESET_ALL))
        print("[%s] = %s (%s %%)\t[%s] = %s (%s %%) (max-level: %s)" % (
            Fore.CYAN + Style.BRIGHT + "Min. Grids" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str((ngrids_min ** 3)) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.round(100 * (ngrids_min ** 3) / int(ngrid), decimals=2)) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Max Grids" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ngrids_max ** 3) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.round(100 * (ngrids_max ** 3) / int(ngrid), decimals=2)) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + max_lev + Style.RESET_ALL,
        ))
        print("#" + ("-") * 27 + Fore.GREEN + Style.BRIGHT + "  END  " + Style.RESET_ALL + ("-") * 27 + "#")

    else:
        print("[%s] = %s\n[%s] = %s\t\t [%s] = %s" % (
            Fore.CYAN + Style.BRIGHT + "ngridmax" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ngrid) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "npartmax" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(npart) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Total Memory Required" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + mem_val_string + Style.RESET_ALL))

        # - Allocation -#
        print("#" + ("-") * 24 + Fore.GREEN + Style.BRIGHT + "  Allocation  " + Style.RESET_ALL + ("-") * 24 + "#")
        print("[%s] = %s (%s CPUs)\n\t{Dark Matter: %s (%s CPUs), Baryonic: %s (%s CPUs)}" % (
            Fore.CYAN + Style.BRIGHT + "Total Particles" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(sum(list(ic_parts))) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.ceil(sum(list(ic_parts)) / float(npart))) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ic_parts[0]) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.ceil(ic_parts[0] / float(npart))) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ic_parts[1]) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.ceil(ic_parts[1] / float(npart))) + Style.RESET_ALL,
        ))
        # - AMR Statistics -#
        print("#" + ("-") * 24 + Fore.GREEN + Style.BRIGHT + "  AMR Stats  " + Style.RESET_ALL + ("-") * 24 + "#")
        print("[%s] = %s" % (Fore.CYAN + Style.BRIGHT + "Box Size" + Style.RESET_ALL,
                             Fore.RED + Style.BRIGHT + str(np.round(box_size, decimals=3)) + " pc" + Style.RESET_ALL))
        print("[%s] = %s (%s: %s), [%s] = %s (%s: %s)" % (
            Fore.CYAN + Style.BRIGHT + "Min. Level" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(levelmin) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Res" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(min_res) + " pc" + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Max. Level" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(levelmax) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Res" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(max_res) + " pc" + Style.RESET_ALL))
        print("[%s] = %s (%s CPUs)\t[%s] = %s (max-level: %s)" % (
            Fore.CYAN + Style.BRIGHT + "Min. Grids" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str((ngrids_min ** 3)) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(np.ceil((ngrids_min ** 3) / int(ngrid))) + Style.RESET_ALL,
            Fore.CYAN + Style.BRIGHT + "Max Grids" + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + str(ngrids_max ** 3) + Style.RESET_ALL,
            Fore.RED + Style.BRIGHT + max_lev + Style.RESET_ALL
        ))
        print("#" + ("-") * 27 + Fore.GREEN + Style.BRIGHT + "  END  " + Style.RESET_ALL + ("-") * 27 + "#")

    # - performing computations of interest -#


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
    log_print("Running run_RAMSES.py.", _dbg_string, "debug")
    time.sleep(0.1)

    ### Setting up the run ###
    print_title("run_RAMSES %s"%CONFIG["system"]["version"], "Eliza Diggins")

    # Grabbing data
    ########################################################################################################################
    selected_ic_file = file_select(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                   lambda file: ".dat" in file or ".g2" in file,
                                   search_for_description=False)
    selected_ic_path = os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"], selected_ic_file)
    os.system('cls' if os.name == 'nt' else 'clear')
    log_print("Running RAMSES with initial conditions file %s." % selected_ic_path, _dbg_string, "debug")

    # Generating NML data
    ########################################################################################################################
    ramses_configuration_data = read_RAMSES_config()  # reading the RAMSES config.

    # changing defaults to reflect choice of IC file.
    default_temp = list(ramses_configuration_data["CORE"]["ic_file"]) # grab the default tuple
    default_temp[0] = selected_ic_path # setting the IC path
    ramses_configuration_data["ic_file"] = tuple(default_temp) # adding back to settings.

    # grabbing proper settings #
    time.sleep(0.1)  # just waiting for prints to finish.
    ramses_config = get_options(ramses_configuration_data, "RAMSES Configuration")
    time.sleep(0.1)
    os.system('cls' if os.name == 'nt' else 'clear')

    # Generating simulation settings
    ########################################################################################################################

    # getting user input for simulation #
    sim_data = set_simulation_information()
    os.system('cls' if os.name == 'nt' else 'clear')
    ### Auto-generating data if not provided.
    # Setting simulation name #
    if sim_data['SimulationName'] == "None":
        sim_data["SimulationName"] = "Simulation_" + datetime.now().strftime('%m-%d-%Y_H%H')

    # Setting the simulation description
    if sim_data['Description'] == "None":
        sim_data["Description"] = "RAMSES simulation run at %s." % datetime.now().strftime('%m-%d-%Y_%H-%M-%S')

    if sim_data["NMLFile"] == "None":
        # grab the names of the nml files that already exist
        nml_names = [file for file in os.listdir(CONFIG["system"]["directories"]["RAMSES_nml_directory"]) if
                     ".nml" in file]
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
        sim_data["NMLFile"] = os.path.join(CONFIG["system"]["directories"]["RAMSES_nml_directory"], name)
    else:
        name = sim_data["NMLFile"]

    ### Providing additional data ###
    sim_data["ICFile"] = selected_ic_file  # grab the IC file path
    sim_data["SLURMDate"] = datetime.now()
    sim_data["SimulationLocation"] = os.path.join(ramses_output_file, sim_data["SimulationName"])
    sim_data["NMLFile"] = os.path.join(CONFIG["system"]["directories"]["RAMSES_nml_directory"], name)

    ### Generating the sim
    add_simulation(**sim_data)

    # Issuing the memory warning
    ####################################################################################################################
    issue_memory_waring(ramses_config)
    # Generating the SLURM File
    ########################################################################################################################

    # writing the .nml file.
    nml_path = write_nml(ramses_config, name=name)  # We found the nml path.

    time.sleep(0.1)
    ### Creating the batch script ###
    slurm_name = input("%s[Input] Select a name for the .slurm file. [return to auto-generate]:" % _dbg_string)
    if slurm_name == "":
        slurm_name = "SLURM_RAMSES_%s.slurm" % sim_data["SimulationName"]

    # generating output file #
    if not os.path.exists(sim_data["SimulationLocation"]):
        pt.Path.mkdir(pt.Path(sim_data["SimulationLocation"]), parents=True)

    command_string = command_string % (sim_data["SimulationLocation"],
                                       ramses_exec,
                                       nml_path)
    time.sleep(0.1)
    os.system('cls' if os.name == 'nt' else 'clear')
    write_slurm_script(command_string,
                       name=slurm_name,
                       type="RAMSES",
                       batch=True)
