"""
            Various routines for studying the dynamics of particles
                          Written by: Eliza Diggins

"""
import os
import pathlib as pt
import shutil
import sys

import pandas as pd
import scipy.ndimage

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))

import matplotlib.pyplot as plt
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
import gc
from itertools import repeat
from utils import split
from PyCS_Core.Logging import log_print, make_error, set_log
from PyCS_System.SimulationMangement import SimulationLog, ICLog
from PyCS_Analysis.Analysis_Utils import align_snapshot
from PyCS_Analysis.Images import generate_image_array
import toml
from datetime import datetime
from multiprocessing import current_process
from concurrent.futures import ProcessPoolExecutor
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
# ------------------------------------------------- Sub-Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def mp_get_centers(output_paths: list, temp_directory: str, resolution, width, footprint, ncores):
    """
    Multi-processing find center procedure.
    Parameters
    ----------
    output_paths: (``list``): The list of *absolute paths* to the outputs to be computed.
    temp_directory: (``str``): The location in which to save the temp files.

    Returns: None
    -------

    """
    # DEBUGGING
    # ---------------------------------------------------------------------------------------------------------------- #
    fdbg_string = "%smp_get_centers: " % _dbg_string
    log_print("Attempting to get centers of %s snaps on process %s." % (len(output_paths), current_process().name),
              fdbg_string, "info")

    if not width:
        no_width = True
    else:
        no_width = False

    # COMPUTING
    # ---------------------------------------------------------------------------------------------------------------- #
    for id, output_path in enumerate(output_paths):  # cycle through all of the output paths for this case.
        log_print("Finding center of %s on %s." % (output_path, current_process().name), fdbg_string, "debug")

        # Opening the simulation and proceeding with typical alignment procedures
        # ------------------------------------------------------------------------------------------------------------ #
        snap = pyn.load(output_path)
        align_snapshot(snap)
        time = snap.properties["time"].in_units("Gyr")
        if no_width:
            width = snap.properties["boxsize"] / 8
        # Generating the image array
        # ------------------------------------------------------------------------------------------------------------ #
        image_array = generate_image_array(snap, "rho", families=["dm"], width=width, resolution=resolution)

        #- Gabage collection -#
        del snap
        gc.collect()
        # - Image manipulations - #
        image_array = np.log10(image_array)  # reduce to a logarithm for easier processing.

        # grabbing maxima
        tmp_max = (image_array == scipy.ndimage.maximum_filter(image_array, footprint, mode="constant", cval=0))

        densities = sorted([image_array[tuple(j)] for j in np.argwhere(tmp_max == True)], reverse=True)[:ncores]

        cores = [np.argwhere(image_array == d)[0] for d in densities]

        log_print("Located %s maximal cores as %s in array coordinates." % (ncores, cores), fdbg_string, "debug")

        # - Unit test dump management -#
        if CONFIG["system"]["system_testing_debug"]:
            fig = plt.figure()
            ax1 = fig.add_subplot(111)
            ax1.imshow(image_array, origin="lower")
            ax1.plot([i[1] for i in cores], [i[0] for i in cores], "ro")
            plt.savefig(os.path.join(CONFIG["system"]["directories"]["unit_test_dump"], "DMPS_get_center_%s_%s.png" % (
            pt.Path(output_path).name, datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))))

            del ax1,fig

        # Analysis
        # ------------------------------------------------------------------------------------------------------------ #
        # grabbing positions
        x, y = np.meshgrid(np.linspace(-width.in_units("kpc") / 2, width.in_units("kpc") / 2, resolution),
                           np.linspace(-width.in_units("kpc") / 2, width.in_units("kpc") / 2, resolution))

        true_x, true_y = [x[c[0], c[1]] for c in cores], [y[c[0], c[1]] for c in cores]

        #- GC -#
        del image_array,densities,cores,tmp_max
        gc.collect()
        # Writing the data
        # ------------------------------------------------------------------------------------------------------------ #
        output_frame = pd.DataFrame({
            "Time": [time for i in true_x],
            "rank": [i + 1 for i in range(len(true_x))],
            "x_val": true_x,
            "y_val": true_y,
            "z_val": [0] * ncores
        })

        # - Writing - #
        output_frame.to_csv(os.path.join(temp_directory, "%s.csv" % pt.Path(output_path).name))
        log_print("Finished %s on %s." % (output_path, current_process().name), fdbg_string, "debug")

    log_print("Finished centers of %s snaps on process %s." % (len(output_paths), current_process().name),
                  fdbg_string, "info")


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_centers(simulation: str,
                resolution: int = 1000,
                width=None,
                footprint: int = 20,
                ncores: int = 2,
                nproc: int = 1) -> None:
    """
    Finds the dark matter halo centers of the given simulation. This can be used to track any number of halos through
    the simulation using the parameter ``ncores``, which controls the number of maxima that we search for in the processing.


    Parameters

    ----------

    simulation: (``str``) The ``SimulationName`` that you want to process.

    resolution: (``int``) The resolution of the image we are going to use to determine the correct value.

    width: (``pyn.units.CompositeUnit``): The desired width of the image used for the co-location process.

    footprint: (``int``) The interpolation footprint size. Larger values are less coarse.

    ncores: (``int``) The number of peaks that the algorithm will locate and the resulting number of data points.

    nproc: (``int``) The number of processes to use in the computation.

    Returns: None.

    -------

    """
    # DEBUGGING
    # ---------------------------------------------------------------------------------------------------------------- #
    fdbg_string = "%sget_centers: " % _dbg_string
    log_print("Attempting to fetch centers for the simulation %s." % simulation, fdbg_string, "debug")

    # SANITIZING INPUT AND LOCATING THE SIMULATION
    # ---------------------------------------------------------------------------------------------------------------- #
    # - Finding the simulation data from the name -#
    try:
        simulation_key = simlog._keys_from_name(simulation)[0]
        log_print("Determined that %s <-> %s." % (simulation_key, simulation), fdbg_string, "debug")
    except IndexError:
        make_error(ValueError, fdbg_string,
                   "The simulation %s couldn't be found in the loaded Simlog. Please check the configuration." % simulation)
        return None

    # - Finding the corresponding output directory and loading a list of outputs. -#
    output_directories = [os.path.join(simlog[simulation_key]["SimulationLocation"], directory) for directory in
                          os.listdir(simlog[simulation_key]["SimulationLocation"]) if
                          "output" in directory]

    if not len(output_directories):  # The outputs are empty
        log_print("Failed to find any output files for this simulation. Exiting.", fdbg_string, "debug")
        return None

    # Managing the dataset's directory
    # ------------------------------------------------------------------------------------------------------------------#
    tmp_output_directory = os.path.join(CONFIG["system"]["directories"]["temp_directory"],
                                        "Dyn_%s_%s" % (simulation, datetime.now().strftime('%m-%d-%Y_%H-%M-%S')))

    if os.path.exists(tmp_output_directory):
        shutil.rmtree(tmp_output_directory)
        pt.Path(tmp_output_directory).mkdir(parents=True)
    else:
        pt.Path(tmp_output_directory).mkdir(parents=True)

    # ---------------------------------------------------------------------------------------------------------------- #
    #                                                                                                                  #
    #                                            Performing the computations                                           #
    #                                                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #
    # - Fixing the number of processors -#
    nproc = np.amin([len(output_directories), nproc])  # Prevents empty processes.

    if nproc > 1:
        ## We are using multiprocessing ##

        # Managing partition
        # --------------------------------------------------------------------------------------------------------------#
        simulation_partition = split(output_directories, nproc)

        # Passing to the process pool
        # --------------------------------------------------------------------------------------------------------------#
        with ProcessPoolExecutor() as executor:
            executor.map(mp_get_centers,
                         simulation_partition,
                         repeat(tmp_output_directory),
                         repeat(resolution),
                         repeat(width),
                         repeat(footprint),
                         repeat(ncores))
    else:
        ## Single Process implementation ##
        mp_get_centers(output_directories, tmp_output_directory, resolution, width, footprint, ncores)

    # Joining into database
    # ------------------------------------------------------------------------------------------------------------------#
    full_frame = pd.DataFrame({})  # this will be populated with the correct frame

    for file in os.listdir(tmp_output_directory):
        tmp_frame = pd.read_csv(os.path.join(tmp_output_directory, file))

        full_frame = full_frame.append(tmp_frame, ignore_index=True)

    if not os.path.exists(os.path.join(CONFIG["system"]["directories"]["datasets_directory"], simulation)):
        pt.Path(os.path.join(CONFIG["system"]["directories"]["datasets_directory"], simulation)).mkdir(parents=True)
    full_frame.to_csv(os.path.join(CONFIG["system"]["directories"]["datasets_directory"], simulation, "centers.csv"),index=False)
    shutil.rmtree(tmp_output_directory)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT")
    # Making the bridge object
    get_centers("TestSim")
