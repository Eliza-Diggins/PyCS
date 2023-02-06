"""

    Functions having to do with profiles and plots of data extracted from simulations.

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Core.Logging import set_log, log_print, make_error
import matplotlib.pyplot as plt
import gc
import warnings
from multiprocessing import current_process
from PyCS_Analysis.Analysis_Utils import align_snapshot,make_pseudo_entropy,make_mach_number,generate_xray_emissivity
from PyCS_System.SimulationMangement import SimulationLog
from PyCS_Analysis.builtin_functions import hydrostatic_mass
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from utils import split

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)
simlog = SimulationLog.load_default()

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
##- Setting up TEX if it is configured -##
try:
    if CONFIG["Visualization"]["use_tex"]:
        plt.rcParams['text.usetex'] = True
        plt.rcParams['xtick.major.size'] = 8
        plt.rcParams['xtick.minor.size'] = 5
        plt.rcParams['ytick.major.size'] = 8
        plt.rcParams['ytick.minor.size'] = 5
        plt.rcParams['xtick.direction'] = "in"
        plt.rcParams['ytick.direction'] = "in"
except RuntimeError:
    log_print("Failed to load latex.", _dbg_string, "error")

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# ----# PYNBODY KWARGS DEFAULT #----------------------------------------------------------------------------------------#
#   These are used by the plotting functions as the basic input kwargs for the plotting functions. They are added
#   to the input kwargs to create a standardized set of always passed kwargs.
#
__pynbody_profile_defaults = {
    "ndim": CONFIG["analysis"]["profiles"]["profile_ndim"],
    "nbins": CONFIG["analysis"]["profiles"]["nbins"],
    "type": CONFIG["analysis"]["profiles"]["type"],
    "rmin": None,
    "rmax": None
}  # Kwargs to pass through pyn.analysis.profile.Profile

# ---# QUANTITY SPECIFIC DEFAULTS #-------------------------------------------------------------------------------------#
#   These dictionaries carry kwargs specific to each quantity that gets passed into either the profiles or
#   the pyn.plot.sph.image() function.
#
__quantities = {
    "vx": {
        "unit": {
            3: CONFIG["units"]["default_velocity_unit"],
            2: CONFIG["units"]["default_velocity_unit"]
        },
        "fancy": "x Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "vy": {
        "unit": {
            3: CONFIG["units"]["default_velocity_unit"],
            2: CONFIG["units"]["default_velocity_unit"]
        },
        "fancy": "y Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "vz": {
        "unit": {
            3: CONFIG["units"]["default_velocity_unit"],
            2: CONFIG["units"]["default_velocity_unit"]
        },
        "fancy": "z Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "temp": {
        "unit": {
            3: CONFIG["units"]["default_temperature_unit"],
            2: CONFIG["units"]["default_temperature_unit"]
        },
        "fancy": "Temperature",
        "families": ["gas"]
    },
    "density": {
        "unit": {3: CONFIG["units"]["default_density_unit"],
                 2: CONFIG["units"]["default_surface_density_unit"]},
        "fancy": "Density",
        "families": ["gas", "stars", "dm"]
    },
    "mass_enc": {
        "unit": {
            3: CONFIG["units"]["default_mass_unit"],
            2: CONFIG["units"]["default_mass_unit"]
        },
        "fancy": "Enclosed Mass",
        "families": ["gas", "stars", "dm"]
    },
    "dyntime": {
        "unit": {3: "Myr",
                 2: "Myr"},
        "fancy": "Dynamical Time",
        "families": ["gas", "stars", "dm"]
    },
    "g_spherical": {
        "unit": {3: "m s^-2",
                 2: "m s^-2"},
        "fancy": "Spherical Potential",
        "families": ["gas", "stars", "dm"]
    },
    "p": {
        "unit": {3: "N m^-2",
                 2: "N m^-2"},
        "fancy": "Pressure",
        "families": ["gas"]
    },
    "entropy": {
        "unit": {3: "keV cm^2",
                 2: "keV cm^2"},
        "fancy": "Entropy",
        "families": ["gas"]
    },
    "mach": {
        "unit": {3: "",
                 2: ""},
        "fancy": "Mach Number",
        "families": ["gas"]
    },
    "xray": {
        "unit": {3:"erg cm^-3 s^-1",
                 2:"erg cm^-2 s^-1"},
        "fancy": r"\epsilon^{ff}",
        "families": ["gas"]
    }
}

# ---# PHYSICAL CONSTANTS #---------------------------------------------------------------------------------------------#
boltzmann = 1.380649e-23 * pyn.units.Unit("J K^-1")  # Defining the Boltzmann constant


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Minor Functions -------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

def set_units(qty, ndim):
    """
    Sets the correct default unit for the given qty.
    Parameters
    ----------
    qty: The qty string.

    Returns: The correct unit.
    -------

    """
    return pyn.units.Unit(__quantities[qty]["unit"][ndim])


def fancy_qty(qty):
    """
    Prints a fancy string for the given quantity.
    Parameters
    ----------
    qty

    Returns
    -------

    """
    return __quantities[qty]["fancy"]


def fix_array_u(array, qty, units):
    """
    Run on all outputting arrays using the fixed units and the quantity. This can be used to correct for issues in the array ahead of time.
    **UNIT-ED**
    Parameters
    ----------
    array: The array to fix.
    qty: The quantity to use.
    units: The units that we actually want to use.

    Returns: fixed array.
    -------

    """
    if qty == "temp" and units != "K":
        return array * float(boltzmann.in_units("%s K^-1" % units)) * pyn.units.Unit("%s K^-1" % units)
    else:
        return array


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def mp_make_profile(arg):
    """
    Multiprocessing make profile function. The args parameter should have the format

    arg = ([simulations:list,output_directory,simulation_directory,qty],{**kwargs})

    **simulations**: a list of the simulation directories, i.e. output_00001...

    **output_directory**: The save location for the final profile plot.

    **simulation_directory**: The location of the base simulation directory.

    **qty** the quantity to generate the profile for.

    Parameters
    ----------
    arg: The args and kwargs for the plotting process.

    Returns: None
    -------

    """
    # Intro Debugging
    ########################################################################################################################
    fdbg_string = _dbg_string + "mp_make_profile: "
    log_print("Generating a multiprocessed profile with args %s. [Process: %s]" % (arg, current_process().name),
              fdbg_string, "debug")

    # Main script
    ########################################################################################################################
    args, kwargs = arg  # splitting the args and kwargs out of the tuple
    for snapshot_name in args[0]:
        # We cycle through each of the snapshot locations
        path = os.path.join(args[2], snapshot_name)  # proper location of the snapshot.
        snap = pyn.load(path)  # load the snap shot

        # Snapshot management
        ################################################################################################################
        try:
            align_snapshot(snap)
        except MemoryError:
            log_print("Ran out of memory", fdbg_string, "critical")
            exit()

        # Running main command
        ################################################################################################################
        make_profile_plot(snap, args[3],
                          end_file=os.path.join(args[1], "Profile_%s.png" % (snapshot_name.replace("output_", ""))),
                          **kwargs)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Functions for generating profiles
# ----------------------------------------------------------------------------------------------------------------------#
def _raw_make_profile_plot(snapshot,
                           qty,
                           Lambda=None,
                           Lambda_label=None,
                           profile=None,
                           axes=None,
                           **kwargs):
    """
    Plots the ``qty`` profile of the input ``snapshot``. User can select an additional ``Lambda`` and ``Lambda_label`` to
    overlay on the plot.

    **_raw**: This function is designed to be attached to other axes and therefore has no management for text or titles.
    That functionality should be managed by a different function.


    Parameters
    ----------
    profile: (*optional*) Provide a profile to avoid recalculating in repeated runs.

    snapshot: The snapshot to analyze.

    qty: The quantity to plot.

    Lambda: (*optional*) Additional lambda function to overlay. Should be a function of **default** length units.

    Lambda_label: (*optional*) The label to assign to the ``Lambda`` input.

    save: True to save, False to show.

    end_file: The filename and path to which the figure should be saved.

    kwargs: additional kwargs for pyn.analysis.profile.Profile and plt.plot.

    Returns: None
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%s_raw_make_profile_plot: " % _dbg_string
    log_print("Generating %s profile plot for snapshot %s." % (qty, snapshot), fdbg_string, "debug")
    # Managing profile kwargs
    ####################################################################################################################
    _prof_kwargs = {}  # these are the kwargs we will pass in
    for key, value in __pynbody_profile_defaults.items():
        if key in kwargs:  # the user included it in their list.
            _prof_kwargs[key] = kwargs[key]
            del kwargs[key]
        else:  # not included in the inputted kwargs. We check for None, then add.
            if value != None:
                _prof_kwargs[key] = value
            else:  # These were set to nonetype anyways.
                pass

    # Deriving arrays
    #------------------------------------------------------------------------------------------------------------------#
    ##- deriving arrays -##
    if qty == "entropy":
        make_pseudo_entropy(snapshot)
    elif qty == "mach":
        make_mach_number(snapshot)
    elif qty == "xray":
        generate_xray_emissivity(snapshot)
    # Creating the profile in question
    ####################################################################################################################
    if not profile:
        # - working out which families to generate the profile for -#
        if "family" in kwargs:
            # We have a family kwargs
            try:
                family = [snap_fam for snap_fam in snapshot.families() if snap_fam.name == kwargs['family']][
                    0]  # get the family
            except KeyError:
                # There was no family of this type.
                make_error(ValueError, fdbg_string, "Failed to recognize family input %s" % (kwargs["family"]))
                return None

            # - creating the profile -#
            profile = pyn.analysis.profile.Profile(snapshot[family], **_prof_kwargs)
            del kwargs["family"]
        else:
            # Families was not specified, -> we need to grab allowable families.
            #
            # If the families array is ["gas","dm"], we can just pass through, otherwise we need to restrict.
            #
            if len(__quantities[qty]["families"]) < 2: # We are restricted!
                try:
                    family = [snap_fam for snap_fam in snapshot.families() if snap_fam.name == __quantities[qty]["families"][0]][0]  # get the family
                except KeyError:
                    # There was no family of this type.
                    make_error(ValueError, fdbg_string, "Failed to recognize default family input %s" % (__quantities[qty]["families"][0]))
                    return None
                # Making the correct profile
                profile = pyn.analysis.profile.Profile(snapshot[family], **_prof_kwargs)
            else:
                # We can use !ANY! profile without family restriction so we just pass over.
                profile = pyn.analysis.profile.Profile(snapshot, **_prof_kwargs)

    # Attempting to generate plotted items
    ####################################################################################################################
    # - grabbing the x array -#
    x = profile["rbins"]  # grabbing the x-array

    if "units_x" in kwargs:
        x = x.in_units(kwargs["units_x"])
        del kwargs["units_x"]
    else:
        x = x.in_units(CONFIG["units"]["default_length_unit"])
    # - grabbing the y array -#
    try:
        # We need to fix this array to manage possible unit errors #
        y = fix_array_u(profile[qty], qty, (
            __quantities[qty]["unit"][_prof_kwargs["ndim"]] if "units_y" not in kwargs else kwargs["units_y"]))
    except KeyError:
        make_error(ValueError, fdbg_string, "The quantity %s is not a valid quantity for this profile..." % qty)
        return None

    # - final unit coercion -#

    if "units_y" in kwargs:
        y = y.in_units(kwargs["units_y"])
        del kwargs["units_y"]
    else:
        y = y.in_units(__quantities[qty]["unit"][_prof_kwargs["ndim"]])

    # Setting up plotting
    ####################################################################################################################
    # - grabbing kwargs -#
    # -- getting x-log information --#
    if "logx" in kwargs and kwargs["logx"] == True:
        logx = True
        del kwargs["logx"]
    elif "logx" in kwargs:
        logx = False
        del kwargs["logx"]
    else:
        logx = False

    # -- getting y-log information --#
    if "logy" in kwargs and kwargs["logy"] == True:
        logy = True
        del kwargs["logy"]
    elif "logy" in kwargs:
        logy = False
        del kwargs["logy"]
    else:
        logy = False

    if "label" not in kwargs:
        kwargs["label"] = r"$\mathrm{%s}$"%__quantities[qty]["fancy"]

    #- Checking for lambda kwargs in the kwargs and moving them -#
    if "lambda_kwargs" in kwargs:
        # We have lambda kwargs so we need to extract and remove.
        lambda_kwargs = kwargs["lambda_kwargs"]
        del kwargs["lambda_kwargs"]
    else:
        # ! THERE IS NOT LAMBDA FUNCTION ! We simply pass over and move on
        lambda_kwargs = {} # This will never be used, empty to keep IDE happy.

    # Plotting
    ####################################################################################################################
    # - creating the figure -#
    if not axes:
        fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
        axes = fig.add_subplot(111)

    # - Finding plotting function -#
    if logx and logy:
        plt_func = axes.loglog
    elif logx:
        plt_func = axes.semilogx
    elif logy:
        plt_func = axes.semilogy
    else:
        plt_func = axes.plot

    # - creating the actual plot -#
    plt_func(x, y, **kwargs)

    ##-managing the lambda function -##
    if Lambda != None:  # there is a lambda function
        if isinstance(Lambda, str):
            # This lambda function is actually a string, so we check for built-in options
            if Lambda in ["HSE", "hse"]:
                Lambda = hydrostatic_mass(snapshot, independent_unit=x.units, dependent_unit=y.units)
            else:
                make_error(ValueError, fdbg_string, "Lambda present %s is not valid." % Lambda)
                return None

        # Dealing with the key word args
        plt_func(x, Lambda(x), label=(Lambda_label if Lambda_label else ""), **lambda_kwargs)

    # Returning
    ####################################################################################################################
    return [axes, x, y]


def make_profile_plot(snapshot,
                      qty,
                      Lambda=None,
                      Lambda_label=None,
                      profile=None,
                      save=CONFIG["Visualization"]["default_figure_save"],
                      end_file=CONFIG["system"]["directories"]["figures_directory"],
                      time_units=pyn.units.Unit(CONFIG["units"]["default_time_unit"]),
                      **kwargs):
    """
    Plots the ``qty`` profile of the input ``snapshot``. User can select an additional ``Lambda`` and ``Lambda_label`` to
    overlay on the plot.
    Parameters
    ----------
    profile: (*optional*) Provide a profile to avoid recalculating in repeated runs.

    snapshot: The snapshot to analyze.

    qty: The quantity to plot.

    Lambda: (*optional*) Additional lambda function to overlay. Should be a function of **default** length units.

    Lambda_label: (*optional*) The label to assign to the ``Lambda`` input.

    save: True to save, False to show.

    end_file: The filename and path to which the figure should be saved.

    kwargs: additional kwargs for pyn.analysis.profile.Profile and plt.plot.

    Returns: None
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%smake_profile_plot: " % _dbg_string
    log_print("Generating %s profile plot for snapshot %s." % (qty, snapshot), fdbg_string, "debug")

    # - managing time units -#
    if isinstance(time_units, str):
        time_units = pyn.units.Unit(time_units)

    # - managing ndims -#
    if not "ndim" in kwargs:
        ndim = __pynbody_profile_defaults["ndim"]
    else:
        ndim = kwargs["ndim"]

    # - managing y units -#
    if not "units_y" in kwargs:
        units_y = pyn.units.Unit(str(__quantities[qty]["unit"][ndim]))  # <-This is potentially redundant
    else:
        units_y = pyn.units.Unit(str(kwargs["units_y"]))  # <-This is potentially redundant

    #- managing y limits -#
    if "ylims" in kwargs:
        # checking the length
        if len(kwargs["ylims"]) != 2:
            make_error(IndexError,fdbg_string,"The kwarg 'ylims' has value %s, which is of length %s but must be of length 2."%(kwargs["ylims"],len(kwargs["ylims"])))

        # We have y limits to deal with
        for id,lim in enumerate(kwargs["ylims"]):
                kwargs["ylims"][id] = (lim if isinstance(lim,(float,int)) else (lim.in_units(units_y) if isinstance(lim,pyn.units.CompositeUnit) else (pyn.units.Unit(lim).in_units(units_y) if lim != "None" else "None")))

        ylims = kwargs["ylims"].copy()
        del kwargs["ylims"]
    else:
        ylims = None # There are no y limits to manage or deal with

    # - Managing title -#
    if "title" in kwargs:
        title = kwargs["title"]
        del kwargs["title"]
    else:
        title = ""
    # Creating the figure
    ####################################################################################################################
    fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = fig.add_subplot(111)

    # - Generating the plot on the axes.
    data = _raw_make_profile_plot(snapshot, qty, Lambda=Lambda, Lambda_label=Lambda_label, profile=profile, axes=axes,
                                  **kwargs)

    # - pulling important info out of data -#
    x, y = tuple(data[1:])

    # - managing limits -#
    if ylims:
        # We have y limits
        for id,lim in enumerate(ylims):
            if lim == "None":
                ylims[id] = (np.amax(y) if id == 1 else np.amin(y))

        axes.set_ylim(ylims)


    # - managing text -#
    axes.set_xlabel(r"Radius [$%s$]" % (x.units.latex()))  # setting the x axis
    axes.set_ylabel(r"$\mathrm{%s} \left[%s\right]$" % (__quantities[qty]["fancy"], y.units.latex()))
    axes.set_title(title)

    # - setting general title -#
    plt.title(r"$t = \mathrm{%s\;%s},\;\;\mathrm{Quantity:\;%s}\;[\mathrm{%s}]$" % (
        np.round(snapshot.properties["time"].in_units(time_units), decimals=2),
        time_units.latex(),
        fancy_qty(qty),
        units_y.latex()), fontsize=10)
    # - adding a legend -#
    plt.legend()

    # - adding the grid -#
    plt.grid()

    # Saving
    #########################################################################################################################
    if save:
        plt.savefig(end_file)

        del profile
        axes.cla()
        del axes
        plt.figure().clear()
        plt.clf()
        plt.close('all')
        gc.collect()
    else:
        plt.show()


def make_profiles_plot(snapshot,
                       quantities: list,
                       profile=None,
                       save=CONFIG["Visualization"]["default_figure_save"],
                       end_file=CONFIG["system"]["directories"]["figures_directory"],
                       **kwargs):
    """
    Plots the ``qtys`` of the ``snapshot`` as well as overlayed ``Lambdas``.
    Parameters
    ----------
    profile: (*optional*) Provide a profile to avoid recalculating in repeated runs.

    snapshot: The snapshot to analyze.

    quantities: *dict* [{quantity:"",q_kwargs:{}}]

    Lambda: (*optional*) Additional lambda function to overlay. Should be a function of **default** length units.

    Lambda_label: (*optional*) The label to assign to the ``Lambda`` input.

    save: True to save, False to show.

    end_file: The filename and path to which the figure should be saved.

    kwargs: additional kwargs for pyn.analysis.profile.Profile and plt.plot.

    Returns: None
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%smake_profiles_plot: " % _dbg_string
    log_print("Generating %s profiles plot for snapshot %s." % (quantities, snapshot), fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - Title Management -#
    if "title" in kwargs:
        title = kwargs["title"]
        del kwargs["title"]
    else:
        title = ""

    # - Fixing quantities -#
    if not "ndim" in kwargs:
        ndim = __pynbody_profile_defaults["ndim"]
    else:
        ndim = kwargs["ndim"]
    ##- Are units consistent? -##
    if len(list(set(list([__quantities[qty["quantity"]]["unit"][ndim] for qty in quantities])))) > 1:
        make_error(TypeError, fdbg_string, "Quantities %s are not compatible." % quantities)

    ##- Fixing internals -##
    for quantity in quantities:
        # - Checking that the keys all have a Lambda or None -#
        if not "Lambda" in quantity["q_kwargs"]:
            quantity["q_kwargs"]["Lambda"] = None
            quantity["q_kwargs"]["Lambda_label"] = None
        elif not "Lambda_label" in quantity["q_kwargs"]:
            quantity["q_kwargs"]["Lambda_label"] = None

        # - managing kwargs in the main set that need to be moved to the output set -#
        if "logx" in kwargs:
            quantity["q_kwargs"]["logx"] = kwargs["logx"]
        if "logy" in kwargs:
            quantity["q_kwargs"]["logy"] = kwargs["logy"]
        if "units_y" in kwargs:
            quantity["q_kwargs"]["units_y"] = kwargs["units_y"]
        if "units_x" in kwargs:
            quantity["q_kwargs"]["units_x"] = kwargs["units_x"]

    # Creating the figure
    ####################################################################################################################
    fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = fig.add_subplot(111)

    # - Generating the plot on the axes.
    for quantity in quantities:
        data = _raw_make_profile_plot(snapshot,
                                      quantity["quantity"],
                                      profile=profile,
                                      axes=axes, **quantity["q_kwargs"])

    # - pulling important info out of data -#
    x, y = tuple(data[1:])
    # - managing text -#
    axes.set_xlabel(r"Radius [$%s$]" % (x.units.latex()))  # setting the x axis
    if 'label_y' in kwargs:
        axes.set_ylabel(r"%s [$%s$]" % (kwargs["label_y"], y.units.latex()))
    else:
        axes.set_ylabel(r"%s [$%s$]" % (__quantities[quantities[0]["quantity"]]["fancy"], y.units.latex()))
    axes.set_title(title)
    # - adding a legend -#
    plt.legend()

    # - adding the grid -#
    plt.grid()

    # Saving
    #########################################################################################################################
    if save:
        plt.savefig(end_file)

        del profile
        axes.cla()
        del axes
        plt.figure().clear()
        plt.clf()
        plt.close('all')
        gc.collect()
    else:
        plt.show()


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#


def generate_profile_sequence(simulation_directory, qty, multiprocess=True, nproc=3, **kwargs):
    """
    Generates a sequence of profiles for the simulation using the given simulation and the given qty.
    Parameters
    ----------
    simulation_directory: The location of the simulation datafiles.
    qty: The quantity in question.
    kwargs: The additional kwargs to pass to the plotting system.

    Returns
    -------

    """
    # DEBUGGING
    ########################################################################################################################
    fdbg_string = _dbg_string + "generate_profile_sequence: "
    log_print(
        "Generating %s profile sequence for %s with the following kwargs: %s" % (qty, simulation_directory, kwargs),
        fdbg_string, "debug")

    # SETUP
    ########################################################################################################################
    # - File Management -#
    if not os.path.isdir(simulation_directory):  # Checking that the simulation directory exists
        make_error(OSError, fdbg_string, "The simulation directory %s doesn't appear to exist." % simulation_directory)

    ##- Getting the simulation name -##
    try:
        simulation_name = simlog.match("SimulationLocation", "SimulationName", simulation_directory)[0]
    except Exception:
        ## Something went wrong ##
        simulation_name = pt.Path(simulation_directory).name

    ##- Making sure ndim is set so we have a consistent naming scheme -##
    if not "ndim" in kwargs:
        kwargs["ndim"] = 3

    output_directory = os.path.join(CONFIG["system"]["directories"]["figures_directory"], simulation_name,
                                    "%s-(ndim=%s)_Profiles" % (qty, kwargs["ndim"]),
                                    datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))

    if not os.path.exists(output_directory):
        pt.Path.mkdir(pt.Path(output_directory), parents=True)

    ##- Debugging -##
    log_print("Saving %s figures to %s." % (qty, output_directory), fdbg_string, "debug")

    ### Getting snapshot directories ###
    output_directories = [dir for dir in os.listdir(simulation_directory) if
                          "output" in dir]  # grab all of the output directories.
    log_print("Found %s figures to plot." % len(output_directories), fdbg_string, "debug")

    # Plotting
    ########################################################################################################################
    if multiprocess and nproc > 1:
        # MULTIPROCESSING
        ####################################################################################################################
        # - Creating the partition -#
        partition = split(output_directories, nproc)  # Maximally efficient splitting for the partition.

        arg = [([partition[i], output_directory, simulation_directory, qty], kwargs) for i in range(len(partition))]
        with ProcessPoolExecutor() as executor:
            executor.map(mp_make_profile, arg)

    else:
        for output_direct in output_directories:  # we are plotting each of these.
            snap_number = output_direct.replace("output_", "")  # this is just the snapshot number

            # - Cleanup -#
            snapshot = pyn.load(os.path.join(simulation_directory, output_direct))

            align_snapshot(snapshot)

            # - Plotting -#
            make_profile_plot(snapshot, qty, end_file=os.path.join(output_directory, "Profile_%s.png" % snap_number),
                              save=True,
                              **kwargs)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT", level=10)
    data = pyn.load("/home/ediggins/PyCS/RAMSES_simulations/TestSim/output_00500")
    align_snapshot(data)
    make_profile_plot(data, "temp", save=False, color="red")
