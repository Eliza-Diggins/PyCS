"""
            Various routines for studying the dynamics of particles
                          Written by: Eliza Diggins

"""
import os
import pathlib as pt
import sys

import pandas as pd

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Core.Logging import log_print, make_error, set_log
from PyCS_System.SimulationMangement import SimulationLog, ICLog
from PyCS_Analysis.Analysis_Utils import align_snapshot
import toml
import numpy as np
import gc

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
    fdbg_string = "%sget_binary_info: " % _dbg_string
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
Wrapper class for the standard ``pyn.bridge.Bridge`` object from ``pynbody``.

The intention is to allow the user to load a ``HaloBridge`` object centered on a single input: ``simulation_name`` and in
doing so track the **DM particles** through the duration of the simulation by generating ``pyn.bridge.Bridge`` objects between
the ``self.dm`` object which comes from the first snapshot and the DM from the subsequent snapshot.

-----------

**Methods**

* ``HaloBridge.__init__:`` Loads the ``HaloBridge`` object from the ``simulation_name``. This simulation name must be findable in the initial conditions log ``iclog`` and in the simulation log ``simlog``.

* ``HaloBridge._load_filters:`` This protected method lets the ``HaloBridge`` object load the parameter data found in ``iclog`` and use it to find the spherical filters that will allow us to track DM particles between simulation snapshots. Generates ``self.filters`` with type ``list`` which holds a filter for each halo.

* ``HaloBridge.get_bridge(snapshot):`` This method takes a snapshot (``pyn.snapshot.SimSnap``) and generates (and returns) a bridge (``self.bridge``) which links the ``self.dm`` halo and the snapshot DM halo ``snapshot.dm``.



"""
    cdbg_string = "%sHaloBridge:" % _dbg_string

    # ----------------------------------------------------------------------------------------------------------------------#
    # DUNDER METHODS
    # ----------------------------------------------------------------------------------------------------------------------#
    def __init__(self, simulation_name: str):
        """
        Initializes the ``HaloBridge`` Class. Requires a ``simulation_name`` (``str``) which is used to locate the base snapshot.

        Parameters

        ----------

        simulation_name : (``str``) Name of the simulation that is being loaded from ``simlog``.
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
            # We didn't find the simulation that we put in.
            make_error(ValueError, fdbg_string,
                       "Failed to find the corresponding location or IC file for simulation named %s." % simulation_name)

        # - Fetching the IC file information from the IC logging system.
        try:
            self.ic_data = iclog[self.simulation_ic]
        except KeyError:
            # We couldn't find the IC data in the log.
            make_error(KeyError, fdbg_string, "Failed to find the IC file %s in the IC log." % self.simulation_ic)

        # Loading Binary Data #
        self.binary_data = get_binary_info(self.ic_data)
        # Loading the dm halo #
        # --------------------------------------------------------------------------------------------------------------#
        ##- Loading the snapshot -##
        try:
            temp_snapshot = pyn.load(os.path.join(self.simulation_location, "output_00001"))
        except OSError:
            make_error(OSError, fdbg_string, "Failed to open the base snapshot (%s) for the simulation %s." % (
                os.path.join(self.simulation_location, "output_00001"), simulation_name))

        ##- Lining things up -##
        align_snapshot(temp_snapshot)

        ##- Setting external -##
        self.dm = temp_snapshot.dm

        # Producing the useful halo filters
        # --------------------------------------------------------------------------------------------------------------#
        self._load_filters()

    # ----------------------------------------------------------------------------------------------------------------------#
    # PROTECTED METHODS
    # ----------------------------------------------------------------------------------------------------------------------#
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

            if not self.binary_data:
                self.binary_data = get_binary_info(self.ic_data)  # grab the IC entry data!
            # creating filters
            self.filters = [
                pyn.filt.Sphere(*self.binary_data[1]),
                pyn.filt.Sphere(*self.binary_data[2])
            ]

        else:
            log_print("IC type was %s. Passing without filters." % self.ic_data["type"], )

    # ----------------------------------------------------------------------------------------------------------------------#
    # METHODS
    # ----------------------------------------------------------------------------------------------------------------------#
    def get_bridge(self, snapshot: pyn.snapshot.SimSnap) -> pyn.bridge.Bridge:
        """
        Generates a ``pyn.bridge.Bridge`` object linking the dark matter halos in ``self.dm`` and the parameter ``snapshot``'s
        dark matter halo (``snapshot.dm``).

        Parameters

        ----------

        snapshot: (``pyn.snapshot.SimSnap``) The snapshot to link. This **must** have a non-empty ``snapshot.dm``.

        Returns: (``pyn.bridge.Bridge``) The linking bridge between the two halos.

        -------

        """
        # debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%s:get_bridge: " % HaloBridge.cdbg_string
        log_print("Generating a bridge between %s and %s." % (self.__str__(), snapshot), fdbg_string, "debug")

        # Creating the bridge
        # --------------------------------------------------------------------------------------------------------------#
        ##- permanent ref -##
        self.bridged_dm = snapshot.dm  # creating a permanent ref. TODO: Better approach?

        ##- making the bridge -##
        self.bridge = pyn.bridge.Bridge(self.dm, self.bridged_dm)

        return self.bridge

    def get_halo_center_filters(self, radius: str = "100 kpc") -> list:
        """
        The ``get_halo_center_filters`` provides the user with a ``list`` of spherical filters (``pyn.filt.Sphere`` objects) which
        are centered on each of the dark matter halos in the simulation, but which have radius ``radius``.

        This can be coupled with the COM computation to track DM cores through simulations!

        Parameters

        ----------

        radius: ( ``str`` , ``int`` , ``float`` ) The radius down to which the sphere should be constrained.

        Returns: (``list[pyn.filt.Sphere]``) The filters in question.

        -------

        """
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%sget_halo_center_filters: " % HaloBridge.cdbg_string
        log_print("Generating halo centered filters of radius %s." % str(radius), fdbg_string, "debug")

        # Setup and Assertions
        # --------------------------------------------------------------------------------------------------------------#
        # - Type checking -#
        assert isinstance(radius, (
            str, float, int)), "The parameter `radius` had a value %s and type %s which was not (str,int,float)." % (
            radius, type(radius))

        # - Coercing the radius into a float object in kpc -#
        if isinstance(radius, (int, float)):
            # The radius is not unit-ed, we convert to float with default length units #
            radius = "%s %s" % (radius, CONFIG["units"]["default_length_unit"])
        else:
            # The radius is already unit-ed (presumably).
            pass

        # - Checking for binary data -#
        if not self.binary_data:
            self.binary_data = get_binary_info(self.ic_data)  # grab the IC entry data!

        # Producing the filters
        # --------------------------------------------------------------------------------------------------------------#
        return [
            pyn.filt.Sphere(radius, self.binary_data[1][1]),
            pyn.filt.Sphere(radius, self.binary_data[2][1])
        ]


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def find_halo_center(simulation: str, nproc=1):
    """
    Locates the centers of mass for each of the halos present in the simulation.

    **Process**:

    1. We first check the simulation log (``SimLog``) for the entry with ``SimulationName==simulation``.

    2. Once that process has been completed, we check for the type of the ICs. If the IC is not binary, then nothing is done and a warning is raised.

    3. If the simulation is binary, we build a ``HaloBridge`` object and then search through each snapshot to find the COM.

    Parameters

    ----------

    simulation: The simulation name for the simulation that is being analyzed.
    nproc: The number of processors to use.

    Returns: None

    -------

    """
    # Logging
    # ------------------------------------------------------------------------------------------------------------------#
    fdbg_string = "%sfind_halo_center: " % _dbg_string
    log_print("Attempting to find COMs for simulation %s." % simulation, fdbg_string, "debug")

    # SETUP
    # ------------------------------------------------------------------------------------------------------------------#
    # - Grabbing the simulation data from the SimLog -#
    try:
        simulation_log_key = simlog._keys_from_name(simulation)[0]
        simulation_log_data = simlog[simulation_log_key]
    except IndexError:
        make_error(IndexError, fdbg_string,
                   "The simulation with SimulationName=%s was not found in default simlog." % simulation)
        return None

    # - Checking on the IC type -#
    try:
        ic_type = iclog[simulation_log_data["ICFile"]]["type"]
    except KeyError:
        make_error(KeyError, fdbg_string,
                   "Failed to find the matching ICLog entry for %s." % simulation_log_data["ICFile"])
        return None

    ##- Checking the type -##
    if ic_type != "cluster-binary":
        log_print("The simulation %s is not a binary cluster, it is a %s. Exiting..." % (simulation, ic_type),
                  fdbg_string, "warning")
        return None

    # - Creating the bridge object -#
    hbridge = HaloBridge(simulation)  # Creating the halo bridge

    # ------------------------------------------------------------------------------------------------------------------#
    #                                                    Processing                                                    #
    # ------------------------------------------------------------------------------------------------------------------#
    #   TODO: Add multiprocessing ---> This probably requires some precession with pickling.
    #   1. Locate all of the outputs and cycle through each one.
    #   2. Generate a smoothed DM map and then filter through each of the DM filters in the halo bridge.
    #   3. Find the maximal point and mark it.
    # ------------------------------------------------------------------------------------------------------------------#
    # SETUP
    # ------------------------------------------------------------------------------------------------------------------#
    # - Getting everything set up -#
    output_paths = [os.path.join(simulation_log_data["SimulationLocation"], directory) for directory in
                    os.listdir(simulation_log_data["SimulationLocation"])]
    log_print("Found %s outputs for the simulation %s." % (len(output_paths), simulation), fdbg_string, "debug")

    # - Setting up the output dictionary -#
    output_dict = {
        "OutputNumber": [],
        "Time": [],
        "H1_x": [],
        "H1_y": [],
        "H1_z": [],
        "H2_x": [],
        "H2_y": [],
        "H2_z": []
    }

    # MAIN
    # ------------------------------------------------------------------------------------------------------------------#
    for output_path in output_paths:  # Cycle through each output
        # LOADING THE OUTPUT
        # --------------------------------------------------------------------------------------------------------------#
        log_print("Attempting to get halo COM from output at %s." % output_path, fdbg_string, "debug")

        # - loading
        snapshot = pyn.load(output_path)  # load the snapshot
        align_snapshot(snapshot)  # aligning

        # - Creating necessary arrays -#
        snapshot.dm["smooth"] = pyn.sph.smooth(snapshot.dm)
        snapshot.dm["rho"] = pyn.sph.rho(snapshot.dm)

        # - Creating the bridge object -#
        bridge = hbridge.get_bridge(snapshot)

        # Finding the COMs
        # --------------------------------------------------------------------------------------------------------------#
        o1, o2 = bridge(hbridge.dm[hbridge.filters[0]]), bridge(
            hbridge.dm[hbridge.filters[1]])  # Transport the centers to the new snapshot.

        # - Finding the centers -#
        c1, c2 = o1[np.where(o1["rho"] == np.amax(o1["rho"]))]["pos"].in_units(CONFIG["units"]["default_length_unit"])[0], \
                 o2[np.where(o2["rho"] == np.amax(o2["rho"]))]["pos"].in_units(CONFIG["units"]["default_length_unit"])[0]

        data_dict = {
            "OutputNumber": [str(pt.Path(output_path).name).replace("output_", "")],
            "Time": [snapshot.properties['time'].in_units(CONFIG["units"]["default_time_unit"])],
            "H1_x": [c1[0]],
            "H1_y": [c1[1]],
            "H1_z": [c1[2]],
            "H2_x": [c2[0]],
            "H2_y": [c2[1]],
            "H2_z": [c2[2]]
        }

        output_dict = {key: value + data_dict[key] for key, value in output_dict.items()}

        # cleanup
        # --------------------------------------------------------------------------------------------------------------#
        del o1, o2, data_dict, bridge, snapshot
        gc.collect()

    # Generating the dataset files
    #------------------------------------------------------------------------------------------------------------------#
    #- Creating the directory if necessary -#
    if not os.path.exists(os.path.join(CONFIG["system"]["directories"]["datasets_directory"],simulation)):
        pt.Path(os.path.join(CONFIG["system"]["directories"]["datasets_directory"],simulation)).mkdir(parents=True)
        simlog.log[simulation_log_key]["DatasetsLocation"] = os.path.join(CONFIG["system"]["directories"]["datasets_directory"],simulation)
        simlog._write()

    #- saving the data -#
    oframe = pd.DataFrame(output_dict)
    oframe.to_csv(os.path.join(CONFIG["system"]["directories"]["datasets_directory"],simulation,"halo_center.csv"))


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT")
    # Making the bridge object
    print(find_halo_center("ColTest", nproc=1))
