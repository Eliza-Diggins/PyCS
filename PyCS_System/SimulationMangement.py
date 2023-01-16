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
from datetime import datetime
import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import toml
import warnings
from tqdm import tqdm

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Functions ---------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Classes ---------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
class ItemLog:
    """
    This is the core logging item which is inherited by both the IC logger and the Simulation Logger.


    """
    # - debugging variables -#
    cdbg_string = "%sItemLog:" % _dbg_string

    def __init__(self, path=None):
        """
        Initializes the ItemLog object.

        Parameters
        ----------
        path: The path to the log.
        """
        # Path Management
        ################################################################################################################
        self.path = path
        if path and os.path.isfile(path):
            # This path exists and it was specified; this should be usable
            self.log = toml.load(path)
        elif path:
            raise OSError("The path %s doesn't exist." % path)
        else:
            self.log = {}

    def __repr__(self):
        return "<ItemLog item @ %s>" % self.path

    def __str__(self):
        return str(self.log)

    def __len__(self):
        return len(self.log)

    def _write(self):
        if self.path:
            with open(self.path, "w") as file:
                toml.dump(self.log, file)
        else:
            pass

    def __getitem__(self, item):
        return self.log[item]

    def __setitem__(self, key, value):

        # adding
        self.log[key] = value

        # saving changes #
        if self.path:
            with open(self.path, "w") as file:
                toml.dump(self.log, file)
        else:
            pass

    def __delitem__(self, key):

        del self.log[key]
        # saving changes #
        if self.path:
            with open(self.path, "w") as file:
                toml.dump(self.log, file)
        else:
            pass

    def __contains__(self, item):
        if item in self.log:
            return True
        else:
            return False

    def match(self, inkey, outkey, value):
        """
        Finds the value of the matching ``inkey`` in the ``outkey``

        Parameters
        ----------
        inkey: The key of the value we are going to give
        outkey: The outkey we want data from.
        value: The value we are trying to look up.

        Returns: list of matched values
        -------

        """
        matches = []  # This is where we will store the matches

        for key, item in self.log.items():
            if inkey in item and outkey in item:  # Does this entry actually have the key in question?
                if item[inkey] == value:
                    matches.append(item[outkey])
                else:
                    pass
            else:
                pass
        return matches

    def items(self):
        return self.log.items()
    def values(self):
        return self.log.values()
    def keys(self):
        return self.log.keys()

    def columns(self,type="all"):
        if type not in ["all","any"]:
            raise ValueError("type must be all or any.")

        any_col = [] # here we store all columns no matter what
        all_cols = [] # the ones we eventually return

        for id,value in enumerate(self.values()):
            val_cols = list(value.keys()) # these are the new keys here.

            any_col = list(set(any_col+val_cols)) # these are the any columns

            if id == 0:
                all_cols = val_cols
            else:
                all_cols = [item for item in val_cols if item in all_cols]

        if type == "all":
            return all_cols
        else:
            return  any_col




class SimulationLog(ItemLog):
    """
    This is a fully functioning Simulation log
    """
    cdbg_string = "%sSimulationLog:" % _dbg_string

    def __init__(self, path=None):

        # Initializing the log
        ################################################################################################################
        ItemLog.__init__(self, path=path)

        # Checking for core updates
        ################################################################################################################
        if path:
            # We only do this if a path is given because it would otherwise be empty.
            for entry,data in self.items():
                # cycle through all of the data and pull things in #
                if "SimulationLocation" in data:
                    # let's check for outputs #
                    try:
                        n_outputs = len([dir for dir in os.listdir(data["SimulationLocation"]) if "output" in dir])
                    except FileNotFoundError:
                        n_outputs = "N.A."

                    self.log[entry]["n_ouputs"] = n_outputs

            self._write()

    @staticmethod
    def load_default():
        """
        Loads the default log location.
        Returns: The log object.
        -------

        """
        # Loading the log from CONFIG location
        ################################################################################################################
        log = SimulationLog(path=os.path.join(CONFIG["system"]["directories"]["bin_directory"],
                                               "Simulation_Logs",
                                               "simlog.log"))

        # UPDATE CHECK
        ################################################################################################################
        #- Checking for missing locations -#
        simlocations = [value["SimulationLocation"] for value in log.values() if "SimulationLocation" in value]

        # look for RAMSES
        try:
            locatable_sims = [os.path.join(CONFIG["system"]["directories"]["RAMSES_simulations_directory"],directory) for directory in os.listdir(CONFIG["system"]["directories"]["RAMSES_simulations_directory"])]
        except FileNotFoundError:
            locatable_sims = []

        # Look for RaYMOND
        try:
            locatable_sims += [os.path.join(CONFIG["system"]["directories"]["RAYMOND_simulations_directory"], directory)
                              for directory in
                              os.listdir(CONFIG["system"]["directories"]["RAYMOND_simulations_directory"])]
        except FileNotFoundError:
            pass

        for id,sim_dir in enumerate(locatable_sims):
            if sim_dir not in simlocations:
                # This is a novel simulation that we want to add #
                log.append({"SimulationLocation":sim_dir,
                            "Software":(
                                "RAMSES" if CONFIG["system"]["directories"]["RAMSES_simulations_directory"] in sim_dir else
                                "RAYMOND_NeS"
                            ),
                            "SimulationName":"UNK-%s-%s"%(datetime.now().strftime('%m-%d-%Y'),id)})

        #- Checking for figure sets -#
        for simulation,data in log.items():
            if data["SimulationName"] in os.listdir(CONFIG["system"]["directories"]["figures_directory"]):
                # There is data in the figures directory.
                log[simulation]["has_figures"] = True
                log[simulation]["GeneratedImages"] = [dir for dir in os.listdir(os.path.join(CONFIG["system"]["directories"]["figures_directory"],data["SimulationName"])) if "Profile" not in dir]
                log[simulation]["GeneratedProfiles"] = [dir for dir in os.listdir(os.path.join(CONFIG["system"]["directories"]["figures_directory"],data["SimulationName"])) if "Profile" in dir]

                log[simulation]["NProfiles"],log[simulation]["NImages"] = len(log[simulation]["GeneratedImages"]),len(log[simulation]["GeneratedProfiles"])
            else:
                log[simulation]["has_figures"] = False

        # Returning
        ################################################################################################################
        return log

    def named_log(self):
        """
        Pulls the names out of the simulations and expresses the log in terms of the names.

        Returns: The log containing the named log data.
        -------
        """
        out_dict = {}

        for item, value in self.log.items():
            if "SimulationName" in value:
                out_dict[value["SimulationName"]] = {key: value for key, value in value.items() if
                                                     key != "SimulationName"}

        return out_dict

    def _keys_from_name(self, name):
        """
        Returns the key with the given Simulation name.
        Parameters
        ----------
        name: The name to look for.

        Returns: The corresponding key.
        -------

        """
        names = {key: (value["SimulationName"] if "SimulationName" in value else None) for key, value in
                 self.log.items()}

        return [key for key, item in names.items() if item == name]

    def append(self, entry):
        """
        Appends the new entry to the simulation log.

        Parameters
        ----------
        entry: dict, the entry to add

        Returns: None
        -------

        """

        # Checking validity
        ################################################################################################################
        if "SimulationName" not in entry:
            raise KeyError("New entries to a SimulationLog object must have a SimulationName.")
        elif len(self._keys_from_name(entry["SimulationName"])) != 0:
            # There is already a simulation with this name in the simulationlog.
            raise KeyError(
                "There is already a simulation with this name (%s) in the simulation log." % entry["SimulationName"])
        else:
            pass  # There is nothing wrong.

        # Forcing some elements
        ################################################################################################################
        for key, fill in zip(["DateCreated", "Software", "ICFile", "NMLFile", "Description", "SimulationLocation"],
                             [datetime.now(), "N.E.S", "None", "None", "None Given", "None"]):
            if key not in entry:
                entry[key] = fill
            else:
                pass

        # Finding the key
        ################################################################################################################
        key_string = "Simulation_%s"
        n = 0

        while True:
            if key_string % n in self.log:
                n += 1
            else:
                simulation_key = key_string % n
                break

        # Adding the simulation
        ################################################################################################################
        self.log[simulation_key] = entry

        # Writing #
        self._write()

    def __delitem__(self, key):
        """
        This is meant to delete the entire simulation from our database.

        Parameters
        ----------
        key: The simulation to delete.

        Returns: None
        -------

        """
        # Collecting deletables
        ################################################################################################################
        deletable_directories = []

        if "NMLFile" in self.log[key]:
            # There is an NML file to delete.
            deletable_directories.append(self.log[key]["NMLFile"])

        if "SimulationLocation" in self.log[key]:
            deletable_directories += [dir for dir in os.listdir(self.log[key]["SimulationLocation"])]
            deletable_directories += [self.log[key]["SimulationLocation"]]

        print(deletable_directories)
        # Deleting
        ################################################################################################################
        for file in tqdm(deletable_directories,desc="Deleting %s"%key):
            if os.path.isdir(file):
                os.system("rm -r '%s'"%file)
            else:
                os.system("rm '%s'"%file)

        # Cleaning up
        ################################################################################################################
        del self.log[key]
        # saving changes #
        if self.path:
            with open(self.path, "w") as file:
                toml.dump(self.log, file)
        else:
            pass

        input("Press [enter] to continue...")


class ICLog(ItemLog):
    """
    This is a fully functioning IC log
    """
    cdbg_string = "%sICLog:" % _dbg_string

    def __init__(self, path=None):

        # Initializing the log
        ################################################################################################################
        ItemLog.__init__(self, path=path)

    @staticmethod
    def load_default():
        """
        Loads the default log location.
        Returns: The log object.
        -------

        """
        return SimulationLog(path=os.path.join(CONFIG["system"]["directories"]["bin_directory"],
                                               "IC_Logs",
                                               "IC_log.log"))
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    simlog = SimulationLog.load_default()
    print(simlog.columns(type="any"))
