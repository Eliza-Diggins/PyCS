"""

    Simulation Management Tools for PyCS
        Written by: Eliza Diggins
        -- Last Check: 12/16 --
------------------------------------------------------------
Simulation Log Format:

[Global]
total_simulations:
last_edit:

[Simulation_n]
name=
date_created=
description=
output_location=
...
"""
import os
import sys
import pathlib as pt

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print, make_error
import toml
from datetime import datetime
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_simulation_logs_directory = os.path.join(CONFIG["system"]["directories"]["bin_directory"],"Simulation_Logs","simlog.log")

_valid_simulation_kwargs = [
    "SimulationName", # This is the name of the simulation. Created by run_RAMSES and run_POR
    "SimulationType", # This is the type of the simulation. run_RAMSES and run_POR
    "ICFile", # The initial condition file location run_RAMSES
    "Description", # The description of the simulation. run_RAMSES
    "SLURMFile", # The associated slurm file
    "NMLFile",
    "SimulationLocation", # The associated location of the simulation
    "SLURMDate", # Date submitted to SLURM
    "NSnapshots", # number of snapshots
    "FiguresLocation",
    "DateCreated",
    "MoviesLocation"
]
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Sub-Functions ------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def read_simulation_log(file:str=_simulation_logs_directory)->dict:
    """
    Reads in the TOML file containing the simulation data.

    Parameters
    ----------
    file: The file to open with the simulation log. This only needs to be set if there is an issue.

    Returns: Dictionary with all of the simulation data.
    -------

    """
    # Start debug #
    fdbg_string = _dbg_string+"read_simulation_log: "
    log_print("Reading simulation log from %s."%file,fdbg_string,"debug")

    # attempting to read the file #
    if not os.path.exists(file): # The file doesn't exist.
        make_error(FileExistsError,fdbg_string,"The file %s doesn't exist. If no prior simulations exist, the simlog file might not yet exist.")
        return {} # these just keep the IDE from yelling at me.
    ### We have the file, we now try to open it ###
    try:
        sim_log = toml.load(file)
    except Exception:
        make_error(SyntaxError,fdbg_string,"TOML failed to load %s. Please check formatting and corruption."%file)
        return {}

    return sim_log


def add_simulation(file:str=_simulation_logs_directory,**kwargs)->None:
    """
    Adds a simulation to the specified file with the kwargs specified. Kwargs must be among the valid kwargs.
    Parameters
    ----------
    file: The file to add to.
    kwargs: The kwargs to use for the entry.

    Returns: None
    -------

    """
    fdbg_string = _dbg_string+"add_simulation: "
    log_print("Adding new entry to file %s. Data: %s."%(file,kwargs),fdbg_string,"debug")

    ### reading the simulation log ###
    try:
        simlog = read_simulation_log(file)
    except Exception: # We don't actually have a log file yet.
        if not os.path.exists(pt.Path(file).parents[0]):
            pt.Path.mkdir(pt.Path(file).parents[0],parents=True)
        with open(file,"w+") as f:
            f.write("[Global]") # We make the header to make it TOML readable.

        simlog = read_simulation_log(file) # if this fails we deserve the error.

    ## Grabbing all simulation names ##
    simulation_names = [simlog[simulation]["SimulationName"] for simulation in simlog.keys() if simulation != "Global"]

    # is this simulation named ?
    sim_name = (kwargs["SimulationName"] if "SimulationName" in kwargs else "No Name") # give it a name if it doesn't have one.

    if sim_name in simulation_names and sim_name != "No Name":
        ### We have a named sim and it is named. We update it instead.
        update_simulation(sim_name,file=file,**kwargs)
    else:
        ### This is a novel simulation and we need to add it.
        if len(simulation_names):
            numb = len(simulation_names)+1
            simlog["Simulation_%s"%(str(numb))] = {"SimulationName":sim_name}
        else:
            numb = 1
            simlog["Simulation_1"]= {"SimulationName":sim_name}

        sim_number = "Simulation_%s"%numb # so we can locate it again.
        ### Adding other necessary data ###
        simlog[sim_number]["DateCreated"]=datetime.now()

        for kwarg in kwargs:
            if kwarg not in ["DateCreated","SimulationName"] and kwarg in _valid_simulation_kwargs: # we want to add it
                simlog[sim_number][kwarg]=kwargs[kwarg]
            else:
                pass


    ### Saving back to disk ###
    os.remove(file)
    with open(file,"w+") as f:
        toml.dump(simlog,f)

def update_simulation(simulation_name,file:str=_simulation_logs_directory,**kwargs):
    """
    Updates the simulation log for the given simulation_name.
    Parameters
    ----------
    file: The simulation log to update.
    simulation_name: The simulation name to update.
    kwargs: The kwargs to change.

    Returns
    -------

    """
    fdbg_string = _dbg_string+"update_simulation: "
    log_print("Updating %s entry in file %s. Data: %s."%(simulation_name,file,kwargs),fdbg_string,"debug")

    ### reading the simulation log ###
    try:
        simlog = read_simulation_log(file)
    except Exception: # We don't actually have a log file yet.
        pt.Path.mkdir(pt.Path(file).parents[0],parents=True)
        with open(file,"w+") as f:
            f.write("[Global]") # We make the header to make it TOML readable.

        simlog = read_simulation_log(file) # if this fails we deserve the error.

    ## Grabbing all simulation names ##
    simulation_names = [simlog[simulation]["SimulationName"] for simulation in simlog.keys() if simulation != "Global"]
    # Does the simulation exist?
    if not simulation_name in simulation_names:
        add_simulation(file=file,Name=simulation_name,**kwargs)
        return None
    else:
        sim_number = "Simulation_%s"%(simulation_names.index(simulation_name)+1) # grab the sim number

    for key,value in kwargs.items():
        simlog[sim_number][key]=value

    ### Saving back to disk ###
    os.remove(file)
    with open(file,"w+") as f:
        toml.dump(simlog,f)

def delete_simulation(simulation_name,file:str=_simulation_logs_directory):
    """
        removes the simulation log for the given simulation_name.
        Parameters
        ----------
        file: The simulation log to update.
        simulation_name: The simulation name to update.

        Returns
        -------

        """
    fdbg_string = _dbg_string + "remove_simulation: "
    log_print("Removing %s entry in file %s." % (simulation_name, file), fdbg_string, "debug")

    ### reading the simulation log ###
    try:
        simlog = read_simulation_log(file)
    except Exception:  # We don't actually have a log file yet.
        pt.Path.mkdir(pt.Path(file).parents[0], parents=True)
        with open(file, "w+") as f:
            f.write("[Global]")  # We make the header to make it TOML readable.

        simlog = read_simulation_log(file)  # if this fails we deserve the error.

    ## Grabbing all simulation names ##
    simulation_names = [simlog[simulation]["SimulationName"] for simulation in simlog.keys() if simulation != "Global"]
    # Does the simulation exist?
    if not simulation_name in simulation_names:
        return None
    else:
        sim_number = "Simulation_%s" % (simulation_names.index(simulation_name) + 1)  # grab the sim number

    del simlog[sim_number]

    for i in range(simulation_names.index(simulation_name)+1,len(simulation_names)-1):
        simlog["Simulation_%s"%(i)] = simlog["Simulation_%s"%(i+1)]

    del simlog["Simulation_%s"%(len(simulation_names))]
    ### Saving back to disk ###
    os.remove(file)
    with open(file, "w+") as f:
        toml.dump(simlog, f)
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT")
    from PyCS_System.text_utils import set_simulation_information
    add_simulation(**set_simulation_information())


