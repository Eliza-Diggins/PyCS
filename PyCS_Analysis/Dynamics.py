"""
            Various routines for studying the dynamics of particles
                          Written by: Eliza Diggins

"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Core.Logging import log_print, make_error, set_log
from PyCS_System.SimulationMangement import SimulationLog, ICLog
import toml
import numpy as np

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
simlog = SimulationLog.load_default()
iclog = ICLog.load_default()


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# IC Management Functions
# ----------------------------------------------------------------------------------------------------------------------#
def get_binary_info(log_entry: dict) -> dict:
    """
    This grabs the binary information out of the log file information and returns it to be used.

    Parameters
    ----------
    log_entry: The log entry from IClog to look for the data from.

    Returns: Dictionary containing the data.
    -------

    """
    # debugging
    # ------------------------------------------------------------------------------------------------------------------#
    fdbg_string = "%s:get_binary_info: " % _dbg_string
    log_print("Attempting to grab IC file data from IC located at %s" % log_entry["location"], fdbg_string, "debug")

    # - Is this actually a binary cluster? -#
    if log_entry["type"] != "cluster-binary":
        make_error(ValueError, fdbg_string, "The IC file located at %s is not a cluster-binary, it is %s." % (
            log_entry["location"], log_entry["type"]))

    # - Are all the of necessary parameter files loaded? -#
    if len(log_entry["param_files"]) != 3:
        make_error(ValueError, fdbg_string,
                   "Could only locate %s documented parameter files, expected %s." % (len(log_entry["param_files"]), 3))

    # - Are we able to find the right parameter file for our purposes? -#
    try:
        parameter_file_path = [path for path in log_entry["param_files"] if "%INFO%" in path][0]
    except IndexError:
        make_error(IndexError, fdbg_string,
                   "The IC file located at %s does not appear to have an associated group %INFO% file associated with it." %
                   log_entry["location"])

    # grabbing the data
    # ------------------------------------------------------------------------------------------------------------------#
    # - Loading the parameter files described in the IC log -#
    try:
        parameter_data = toml.load(parameter_file_path)  # This should be params%INFO%...
    except FileNotFoundError:
        make_error(FileNotFoundError, fdbg_string,
                   "Failed to locate the file %s. Has it been generated?" % parameter_file_path)

    # - pulling necessary information -#
    ##- Pulling general information -##
    impact_parameter, distance = (float(parameter_data["General"]["Impact Parameter"][0]),
                                  float(parameter_data["General"]["Initial Distance"][0]))

    ##- Pulling cluster information -##
    cluster_masses = {"Cluster 1": 0, "Cluster 2": 0}

    for cluster_number in ["1", "2"]:
        # - Did we exclude anything? -#
        tmp_no_dm = parameter_data["Cluster %s" % cluster_number]["tags"]["--no-dm"][0]
        tmp_no_gas = parameter_data["Cluster %s" % cluster_number]["tags"]["--no-gas"][0]

        # - Grabbing the masses -#
        if tmp_no_dm == "False":  # We have DM,
            cluster_masses["Cluster %s" % cluster_number] += float(
                parameter_data["Cluster %s" % cluster_number]["dark_matter"]["M_dm"][0])
        if tmp_no_gas == "False":  # We have DM,
            cluster_masses["Cluster %s" % cluster_number] += float(
                parameter_data["Cluster %s" % cluster_number]["gas"]["M_gas"][0])

        # - multiplying and uniting -#
        cluster_masses["Cluster %s" % cluster_number] *= 10e10

    # COMPUTING
    # ------------------------------------------------------------------------------------------------------------------#

    # - Center of Mass Calculations -#
    #
    # NOTE: because the first cluster starts at 0,0,0 and we then place in the second, we can ignore #1 during this
    #
    COM = (cluster_masses["Cluster 2"] / (
            cluster_masses["Cluster 1"] + cluster_masses["Cluster 2"])) * pyn.array.SimArray(
        [distance, impact_parameter, 0], "kpc")

    # - Finding halo locations -#
    #
    # NOTE: We need to find the maximum circular radius we can incorporate.
    #
    # Starting with the untranslated locations #
    p1, p2 = pyn.array.SimArray([0., 0., 0.], "kpc"), pyn.array.SimArray([distance, impact_parameter, 0], "kpc")

    # translating
    p1 -= COM;
    p2 -= COM

    # - Halo Size Computation -#
    r1, r2 = (float(parameter_data["Cluster 1"]["global"]["truncation_radius"][0]),
              float(parameter_data["Cluster 2"]["global"]["truncation_radius"][0]))

    # Checking if that is okay:
    distance = np.sqrt(distance ** 2 + impact_parameter ** 2)

    if r1 + r2 > distance:
        r1, r2 = distance / 2, distance / 2
    else:
        pass

    return {1: [r1, p1],
            2: [r2, p2]}


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Classes --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
class HaloBridge:
    """
    The ``HaloBridge`` class is a wrapper for the standard bridge in pyn.bridge.Bridge.

    The idea is that we can load an initial condition RAMSES output (00001) and fetch the dark matter out, then setup
    the bridge.
    """
    cdbg_string = "%s:HaloBridge:" % _dbg_string

    def __init__(self, simulation_name: str):
        """
        Initializes the ``HaloBridge`` class. You can choose how we locate the initial state.

        Parameters
        ----------
        simulation_name: The name of the simulation. We will use this to find the snapshot. (1st)
        simulation_directory: The directory of the simulation. We can use this to find the snapshot. (2nd)
        snapshot: The snapshot itself, either as a string. (3rd)
        """
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%s__init__: " % HaloBridge.cdbg_string
        log_print("Initializing HaloBridge object with simulation name %s." % simulation_name, fdbg_string, "debug")

        # Setup
        # --------------------------------------------------------------------------------------------------------------#
        try:
            # Grabbing the simulation location from the simulation name and getting the ic file
            self.simulation_location, self.simulation_ic = \
                simlog.match("SimulationName", "SimulationLocation", simulation_name)[0], \
                simlog.match("SimulationName", "ICFile", simulation_name)[0]
        except IndexError:
            make_error(ValueError, fdbg_string,
                       "Failed to find the corresponding location or IC file for simulation named %s." % simulation_name)

        # - Fetching the IC file information from the IC logging system.
        try:
            self.ic_data = iclog[self.simulation_ic]
        except KeyError:
            make_error(KeyError, fdbg_string, "Failed to find the IC file %s in the IC log." % self.simulation_ic)

        # Pulling necessary data
        # --------------------------------------------------------------------------------------------------------------#
        # loading
        temp_load_snapshot = pyn.load(os.path.join(self.simulation_location, "output_00001"))

        self.dm = temp_load_snapshot.dm.copy()

        # unloading
        del temp_load_snapshot

        # Producing the useful halo filters
        # --------------------------------------------------------------------------------------------------------------#
        self._load_filters()

    def _load_filters(self):
        """
        This routine loads the corresponding filters based on the IC data provided.

        **Types**:

        1 *Binary*: Produces 2 filters, one for each of the clusters

        2 *Singular*: Produces no filters.

        -------

        """
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%s:_load_filters: " % HaloBridge.cdbg_string
        log_print("Attempting to load filters for %s." % self.__str__(), fdbg_string, "debug")

        # Reading in data
        # --------------------------------------------------------------------------------------------------------------#
        if self.ic_data["type"] == "cluster-binary":
            # This is a binary IC file which needs to be managed.
            #
            #    The approach here is to use the IC data to find COM and cluster locations, then
            #        we can generate the locations from that.

            binary_data = get_binary_info(self.ic_data)  # grab the IC entry data!

            # creating filters
            self.filters = [
                pyn.filt.Sphere(*binary_data[1]),
                pyn.filt.Sphere(*binary_data[2])
            ]

        else:
            log_print("IC type was %s. Passing without filters." % self.ic_data["type"], )

    def get_bridge(self,snapshot:pyn.snapshot.SimSnap)-> pyn.bridge.Bridge:
        """
        Generates a proper ``pyn.bridge.Bridge`` object between the dark matter data stored in the ``HaloBridge`` object.

        This allows the user to pass a filter (``self.filters[i]``) and ``self.dm`` through the bridge to identify
        those particles in the current snapshot.

        TODO: This may not be parallelizable. We may need to think about how this object could be shared between processes.

        Parameters
        ----------
        snapshot: The snapshot that we are generating the conection with. Should be type ``pynbody.snapshot.SimSnap``

        Returns: None
        -------

        """
        # debugging
        #--------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%s:get_bridge: "%HaloBridge.cdbg_string
        log_print("Generating a bridge between %s and %s."%(self.__str__(),snapshot),fdbg_string,"debug")

        # Creating the bridge
        #--------------------------------------------------------------------------------------------------------------#
        self.bridge = pyn.bridge.Bridge(self.dm,snapshot.dm)

        return self.bridge


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename,output_type="STDOUT")

    bridge = HaloBridge("UNK-01-16-2023-11")
    print(bridge.filters)