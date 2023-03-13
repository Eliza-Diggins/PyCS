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
from PyCS_System.text_utils import file_select, print_title, multi_file_select
from PyCS_System.SpecConfigs import read_RAMSES_config, write_nml, write_slurm_script
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
#- Grabbing the correct executables -#
ramses_exec = CONFIG["system"]["executables"]["RAMSES_exec"]
aqual_exec = CONFIG["system"]["executables"]["AQUAL_exec"]
qumond_exec = CONFIG["system"]["executables"]["QUMOND_exec"]

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
f
    # grabbing the ic location and length
    ic_loc = str(nml_config["CORE"]["ic_file"][0])[1:-1]

    if os.path.isfile(ic_loc):
        snap = pyn.load(ic_loc)
    else:
        outputs = {int(dir.split("_")[1]):dir for dir in os.listdir(ic_loc) if "output" in dir}
        last_output = outputs[np.amax(list(outputs.keys()))]
        snap = pyn.load(os.path.join(ic_loc,last_output))

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

    #------------------------------------------------------------------------------------------------------------------#
    #                               SELECTING INITIAL CONDITIONS FOR THE SIMULATION
    #------------------------------------------------------------------------------------------------------------------#
    # In this phase, the user selects the IC_path, which is the location of the desired simulation start point,
    # be it an actual simulation or an IC file
    #
    #- Grabbing the selected file or simulation.
    selected_ic_path = multi_file_select([CONFIG["system"]["directories"]["initial_conditions_directory"],
                                          CONFIG["system"]["directories"]["RAYMOND_simulations_directory"],
                                          CONFIG['system']['directories']['RAMSES_simulations_directory']],
                                   lambda file: (".dat" in file or ".g2" in file) or "." not in file)

    status = ("SIM" if not os.path.isfile(selected_ic_path) else "IC") # Marks the status for further changes.
    os.system('cls' if os.name == 'nt' else 'clear')
    log_print("Running RAMSES with initial conditions file %s. STATUS=%s." % (selected_ic_path,status), _dbg_string, "debug")

    # GENERATING NML DATA, CLEANING NML, INSERTING TYPE NECESSARY INSTANCES
    #------------------------------------------------------------------------------------------------------------------#
    # In this phase:
    #   1. Reading the NML data: We grab the nml data from the RAMSES config and add the IC_file to the CORE["ic_file"] option.
    #       * This has the effect of allowing the user to either select to continue the simulation in RAMSES or RAYMOND by toggling software.
    #       * If the simulation is being restarted, this information fundamentally isn't used, but it needs to be present in some capacity.
    #   2. User selects RAMSES options. This includes toggling groups and choosing software.
    #       * TODO: At this phase, we need to enforce fidelity with MPI settings.
    #       * If we are continuing a simulation, we can use either software option. If we choose RAMSES, it will include
    #           DICE_PARAMS which are not used anyways. If it's RAyMOND, then RAyMOND parameters will be passed and
    #           We use the "gadget" mode for loading, even though it doesn't work, it doesn't need to!
    #------------------------------------------------------------------------------------------------------------------#
    ramses_configuration_data = read_RAMSES_config()  # reading the RAMSES config.

    # changing defaults to reflect choice of IC file.
    if status == "IC":
        # We need to mark an IC file in the name list.
        default_temp = list(ramses_configuration_data["CORE"]["ic_file"]) # grab the default tuple
        default_temp[0] = "'%s'"%selected_ic_path # setting the IC path
        ramses_configuration_data["CORE"]["ic_file"] = tuple(default_temp) # adding back to settings.
        log_print("RAMSES setting `CORE.ic_file` was set to %s"%selected_ic_path,_dbg_string,"debug")
    else:
        # This is a simulation that is being restarted! We still need to mark
        # Finding the IC File
        log_print("Attempting to locate IC path for simulation located at %s."%selected_ic_path,_dbg_string,"debug")
        try:
            tmp_ic_path = os.path.join(CONFIG["system"]["directories"]["initial_conditions_directory"],
                                       simlog.match("SimulationLocation","ICFile",selected_ic_path)[0])
            log_print("Located IC path for simulation located at %s." % selected_ic_path, _dbg_string,
                      "debug")
        except KeyError:
            raise ValueError("The selected simulation either isn't in the simulation log or doesn't have a simulation location.")

        # Adding to the CORE var
        default_temp = list(ramses_configuration_data["CORE"]["ic_file"]) # grab the default tuple
        default_temp[0] = "'%s'"%tmp_ic_path # setting the IC path
        ramses_configuration_data["CORE"]["ic_file"] = tuple(default_temp) # adding back to settings.
        log_print("RAMSES setting `CORE.ic_file` was set to %s." % tmp_ic_path, _dbg_string, "debug")

    # grabbing proper settings #
    time.sleep(0.1)  # just waiting for prints to finish.
    ramses_config = get_options(ramses_configuration_data, "RAMSES Configuration")
    time.sleep(0.1)
    os.system('cls' if os.name == 'nt' else 'clear')

    #------------------------------------------------------------------------------------------------------------------#
    #                                           GATHERING SIMULATION INFORMATION                                       #
    #------------------------------------------------------------------------------------------------------------------#
    # In This Phase:
    #   1. We fetch simulation information from the user which we will use to update the simulationlog.
    #       * The only difference on STATUS here: new sims get a name!
    #   2. Generate the defaults if the user doesn't specify.
    #       * In this stage, we don't make simulation directories or change IC paths for pre-existing sims.
    #------------------------------------------------------------------------------------------------------------------#
    sim_data = set_simulation_information()
    os.system('cls' if os.name == 'nt' else 'clear')

    log_print("Initial `sim_data` was %s."%sim_data,_dbg_string,"debug")
    #- managing simulation name

    if status == "IC":
        # The simulation doesn't have a name because its coming from a new simulation.
        if sim_data['SimulationName'] == "None":
            log_print("The SimulationName was not set and status was IC, setting to Simulation_%%datetime%%.",_dbg_string,"debug")
            sim_data["SimulationName"] = "Simulation_" + datetime.now().strftime('%m-%d-%Y_H%H')
    else:
        # The simulation already has a name anyways.
        log_print("Found no SimulationName provided by user, but status was %s, so we passed."%status,_dbg_string,"debug")

    #- Managing the description ----> Any user can choose to modify this.
    if sim_data['Description'] == "None":
        log_print("Setting a default description.",_dbg_string,"debug")
        sim_data["Description"] = "%s simulation run at %s." % (ramses_config["CORE"]["software"][0],datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))

    #- Managing the NML File.
    # For existing simulations #
    if sim_data["NMLFile"] == "None" and status == "SIM":
        log_print("No NML file was provided, STATUS=%s. Attempting to fetch name from simlog."%status,_dbg_string,"debug")

        simlog_key = simlog._keys_from_name(simlog.match("SimulationLocation","SimulationName",selected_ic_path)[0])[0]

        if "NMLFile" in simlog[simlog_key] and simlog[simlog_key]["NMLFile"] != "None":
            log_print("Found an NMLFile for the given simulation in the simlog. Using it as the nml name.",_dbg_string,"debug")
            sim_data["NMLFile"] = simlog[simlog_key]["NMLFile"]
            name = sim_data["NMLFile"]
        else:
            log_print("Failed to find an NMLFile for the given simulation. Using the simulation name.",_dbg_string,"debug")
            print(simlog,sim_data,simlog_key)
            name = "%s.nml"%simlog[simlog_key]["SimulationName"]
            log_print("Chose name %s for the NML file."%name,_dbg_string,"debug")

    elif sim_data["NMLFile"] == "None" and status=="IC":
        log_print("There was no specified NML file and the status was from IC file.",_dbg_string,"debug")
        # grab the names of the nml files that already exist
        nml_names = [file for file in os.listdir(CONFIG["system"]["directories"]["RAMSES_nml_directory"]) if
                     ".nml" in file]
        try:
            name = ramses_config["DICE_PARAMS"]["ic_file"][0].split(".")[0][1:] + ".nml"

        except KeyError:
            name = "%s_nml.nml"%(ramses_config["CORE"]["software"][0])

        name_already_exists = name in nml_names
        l = 0
        base_name = name
        while name_already_exists:  # we need to keep fixing up the name until we find something logically reasonable.
            name = base_name.split(".")[0] + "_(%s)" % l + ".nml"
            name_already_exists = name in nml_names
            l += 1
        sim_data["NMLFile"] = os.path.join(CONFIG["system"]["directories"]["RAMSES_nml_directory"], name)
        log_print("Determined that the correct name was %s."%name,_dbg_string,"debug")
    else:
        name = sim_data["NMLFile"]

    #----------------------------------- Providing additional simulation info -----------------------------------------#
    sim_data["SLURMDate"] = datetime.now()
    sim_data["Software"] = ramses_config["CORE"]["software"][0]
    sim_data["NMLFile"] = os.path.join(CONFIG["system"]["directories"]["RAMSES_nml_directory"], name)

    if status == "IC":
        sim_data["ICFile"] = pt.Path(selected_ic_path).name

        # - setting the output location -#
        if "RAYMOND" in sim_data["Software"]:
            sim_data["SimulationLocation"] = os.path.join(raymond_output_file, sim_data["SimulationName"])
        else:
            sim_data["SimulationLocation"] = os.path.join(ramses_output_file, sim_data["SimulationName"])

    ### Generating the sim
    # IF IC--> New simlog item. Otherwise, edit.
    if status == "IC":
        simlog.append(sim_data)
    else:
        simlog_key = simlog._keys_from_name(simlog.match("SimulationLocation","SimulationName",selected_ic_path)[0])[0]
        simlog[simlog_key] = {key:(simlog[simlog_key][key]
                                   if key not in {k:value for k,value in sim_data.items() if value != "None"} else sim_data[key])
                              for key in [*simlog[simlog_key],*sim_data]}
        simlog._write()
        sim_data["SimulationLocation"] = simlog[simlog_key]["SimulationLocation"]
        sim_data["SimulationName"] = simlog[simlog_key]["SimulationName"]

    #------------------------------------------------------------------------------------------------------------------#
    #                                          GENERATING A MEMORY WARNING                                             #
    #------------------------------------------------------------------------------------------------------------------#
    # TODO: We need to implement a differential calculation based on approach.
    issue_memory_waring(ramses_config)

    #------------------------------------------------------------------------------------------------------------------#
    #                                            SLURM FILE GENERATION                                                 #
    #------------------------------------------------------------------------------------------------------------------#
    # writing the .nml file.
    print(name)
    nml_path = write_nml(ramses_config, name=name)  # We found the nml path.

    time.sleep(0.1)
    ### Creating the batch script ###
    slurm_name = input("%s[Input] Select a name for the .slurm file. [return to auto-generate]:" % _dbg_string)
    if slurm_name == "":
        slurm_name = "SLURM_%s_%s.slurm" %(ramses_config["CORE"]["software"][0], sim_data["SimulationName"])

    #------------------------------------------------------------------------------------------------------------------#
    #                                           MANAGING OUTPUT FILES                                                  #
    #------------------------------------------------------------------------------------------------------------------#
    #- Creating the simulation locations if they don't already exist -#
    if not os.path.exists(sim_data["SimulationLocation"]):
        pt.Path.mkdir(pt.Path(sim_data["SimulationLocation"]), parents=True)


    if "RAYMOND_Q" == ramses_config["CORE"]["software"][0]:
        command_string = command_string % (sim_data["SimulationLocation"],
                                           qumond_exec,
                                           nml_path)
    elif "RAYMOND_A" == ramses_config["CORE"]["software"][0]:
        command_string = command_string % (sim_data["SimulationLocation"],
                                           aqual_exec,
                                           nml_path)
    else:
        command_string = command_string % (sim_data["SimulationLocation"],
                                               ramses_exec,
                                               nml_path)
    time.sleep(0.1)
    os.system('cls' if os.name == 'nt' else 'clear')
    write_slurm_script(command_string,
                       name=slurm_name,
                       type=ramses_config["CORE"]["software"][0],
                       batch=True)
