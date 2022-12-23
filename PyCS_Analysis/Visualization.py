"""

        PyCS Analysis Utils for common use

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import sys
import pathlib as pt
import numpy as np
import copy
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Analysis.Analysis_Utils import get_families, align_snapshot
from PyCS_Core.PyCS_Errors import *
import matplotlib.pyplot as plt
from PyCS_System.SimulationMangement import get_simulation_qty
from utils import split
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import current_process
import matplotlib as mpl
import gc

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

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

#----# PYNBODY KWARGS DEFAULT #----------------------------------------------------------------------------------------#
#   These are used by the plotting functions as the basic input kwargs for the plotting functions. They are added
#   to the input kwargs to create a standardized set of always passed kwargs.
#
__pynbody_image_defaults = {
    "cmap": CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"],
    "resolution": CONFIG["Visualization"]["Images"]["default_resolution"],
    "width": CONFIG["Visualization"]["Images"]["default_width"]
} # Kwargs to pass into pyn.plot.sph.image
__pynbody_profile_defaults = {
    "ndim": CONFIG["analysis"]["profiles"]["profile_ndim"],
    "nbins": CONFIG["analysis"]["profiles"]["nbins"],
    "type": CONFIG["analysis"]["profiles"]["type"],
    "rmin": None,
    "rmax": None
} # Kwargs to pass through pyn.analysis.profile.Profile

#---# QUANTITY SPECIFIC DEFAULTS #-------------------------------------------------------------------------------------#
#   These dictionaries carry kwargs specific to each quantity that gets passed into either the profiles or
#   the pyn.plot.sph.image() function.
#
__quantities = {
    "vx": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "x Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "vy": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "y Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "vz": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "z Velocity",
        "families": ["gas", "stars", "dm"]
    },
    "temp": {
        "unit": CONFIG["units"]["default_temperature_unit"],
        "fancy": "Temperature",
        "families": ["gas"]
    },
    "density": {
        "unit": CONFIG["units"]["default_density_unit"],
        "fancy": "Density",
        "families": ["gas", "stars", "dm"]
    },
    "rho": {
        "unit": CONFIG["units"]["default_density_unit"],
        "fancy": "Density",
        "families": ["gas"]
    },
    "mass_enc": {
        "unit": CONFIG["units"]["default_mass_unit"],
        "fancy": "Enclosed Mass",
        "families": ["gas", "stars", "dm"]
    },
    "dyntime": {
        "unit": "Myr",
        "fancy": "Dynamical Time",
        "families": ["gas", "stars", "dm"]
    },
    "g_spherical": {
        "unit": "m s^-2",
        "fancy": "Spherical Potential",
        "families": ["gas", "stars", "dm"]
    },
    "p": {
        "unit": "N m^-2",
        "fancy": "Pressure",
        "families": ["gas"]
    }
}

#---# PHYSICAL CONSTANTS #---------------------------------------------------------------------------------------------#
boltzmann = 1.380649e-23 * pyn.units.Unit("J K^-1")  # Defining the Boltzmann constant


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Minor Functions -------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

def set_units(qty):
    """
    Sets the correct default unit for the given qty.
    Parameters
    ----------
    qty: The qty string.

    Returns: The correct unit.
    -------

    """
    return pyn.units.Unit(__quantities[qty]["unit"])


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


def fix_array(array, qty, units):
    """
    Run on all outputting arrays using the fixed units and the quantity. This can be used to correct for issues in the array ahead of time.
    Parameters
    ----------
    array: The array to fix.
    qty: The quantity to use.
    units: The units that we actually want to use.

    Returns: fixed array.
    -------

    """
    if qty == "temp" and units != "K":
        return array * float(boltzmann.in_units("%s K^-1" % units))
    else:
        return array


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
        return array * float(boltzmann.in_units("%s K^-1" % units)) * pyn.units.Unit(units)
    else:
        return array


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def mp_make_plot(arg):
    """
    Multiprocessing make plot function. The args parameter should have the format

    arg = ([simulations:list,output_directory,simulation_directory,qty],{**kwargs})
    Parameters
    ----------
    arg: The args and kwargs for the plotting process.

    Returns: None
    -------

    """
    # Intro Debugging
    ########################################################################################################################
    fdbg_string = _dbg_string + "mp_make_plot: "
    log_print("Generating a multiprocessed plot with args %s. [Process: %s]" % (arg, current_process().name),
              fdbg_string, "debug")

    # Main script
    ########################################################################################################################
    args, kwargs = arg  # splitting the args and kwargs out of the tuple
    for simulation in args[0]:  # cycle through all of the output folders.
        path = os.path.join(args[2], simulation)
        snap = pyn.load(path)
        # - Aligning the snap -#
        try:
            align_snapshot(snap)
        except MemoryError:
            log_print("Ran out of memory", fdbg_string, "critical")
            exit()
        make_plot(snap, args[3], end_file=os.path.join(args[1], "Image_%s.png" % (simulation.replace("output_", ""))),
                  **kwargs)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# NOTES:
#    generate_image_array maps snapshots -> image arrays,
#       Then, make_plot maps -> snapshots -> images actually saved.
#
#
#
#
#
# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#
def generate_image_array(snapshot, qty, families=None, **kwargs):
    """
    Generates the plot array for a specific snapshot and quantity.
    Parameters
    ----------
    snapshot: The SimSnap object to use in the plotting.
    qty: The qty to plot.
    families: The families to include in the plot. Defaults to all.
    kwargs: Additional kwargs to pass to the plotting system.

    Returns: Numpy array.
    -------

    """
    # DEBUGGING
    ########################################################################################################################
    fdbg_string = _dbg_string + "generate_image_array: "
    log_print("Plotting %s for families %s and qty %s." % (qty, families, snapshot), fdbg_string, "debug")

    # KWARG MANAGEMENT
    ########################################################################################################################

    # - families -#

    if families:  # There are families, we need to get them to a usable format.
        families = get_families(snapshot, families)

        # checking for a reasonable length
        if not len(families):
            make_error(SnapshotError, fdbg_string, "Families %s were not found." % families)
    else:
        families = snapshot.families()

    # - Getting defaults -#

    for key, value in __pynbody_image_defaults.items():  # cycle through all of the defaults
        if key not in kwargs:
            kwargs[key] = value
        else:
            pass

    # - Managing units -#

    if "units" not in kwargs:  # there are not yet specified units
        kwargs["units"] = set_units(qty)

    # - Managing fix units -#

    if qty == "temp":  # ----> we feed this into the fix units function.
        fix_units = kwargs["units"]
        kwargs["units"] = pyn.units.Unit("K")
    else:
        fix_units = kwargs["units"]

    # PLOTTING
    ########################################################################################################################
    # - Generating the empty array -#
    output_array = np.zeros((kwargs["resolution"], kwargs["resolution"]))

    for family in families:
        ### Cycle through each family and generate the image array.
        try:
            output_array += pyn.plot.sph.image(snapshot[family], qty=qty, noplot=True, **kwargs, threaded=False)
            log_print("Plotted family %s for snapshot %s and quantity %s." % (family.name, snapshot, qty),
                      fdbg_string, "info")
        except Exception:
            log_print("Failed to plot family %s for snapshot %s and quantity %s." % (family.name, snapshot, qty),
                      fdbg_string, "error")

    # RETURNING
    ########################################################################################################################
    return fix_array(output_array, qty, fix_units)


def make_plot(snapshot,
              qty,
              families=None,
              save=CONFIG["Visualization"]["default_figure_save"],
              end_file=None,
              time_units=pyn.units.Unit(CONFIG["units"]["default_time_unit"]),
              title=None,
              log=False,
              vmin=None,
              vmax=None,
              length_units=CONFIG["units"]["default_length_unit"],
              **kwargs) -> None:
    """
    Plots the snapshot, qty and families. Saves to an intended location.
    Parameters
    ----------
    save: True to save, False to pass
    end_file: The endfile location.
    snapshot: The snapshot to pass in.
    qty: The qty to plot.
    families: The families to use.
    kwargs: Additional plotting kwargs.

    Returns: None
    -------

    """
    ### Intro Debugging ###
    fdbg_string = _dbg_string + "make:plot: "
    log_print("Making plot of %s for %s." % (qty, snapshot), fdbg_string, "debug")

    ### Managing defaults ###
    # Managing kwargs #
    for key, value in __pynbody_image_defaults.items():  # cycle through all of the defaults
        if key not in kwargs:
            kwargs[key] = value
        else:
            pass

    ### Managing the units ###
    if not "units" in kwargs:
        kwargs["units"] = set_units(qty)
    else:
        kwargs["units"] = pyn.units.Unit(kwargs["units"])

    if isinstance(time_units, str):
        time_units = pyn.units.Unit(time_units)
    # PLOTTING #
    ########################################################################################################################
    ### Making the figure ###
    figure = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = figure.add_subplot(111)

    # - Managing the Extends -# This allows us to set the right ticks and axes.
    numerical_width = float(pyn.units.Unit(kwargs["width"]).in_units(length_units))
    extent = [-numerical_width / 2, numerical_width / 2, -numerical_width / 2, numerical_width / 2]

    # - Getting the data -#
    image_array = generate_image_array(snapshot, qty, families=families, **kwargs)


    #- MANAGING COLORS AND VMIN/VMAX

    if not vmin:
        vmin = np.amin(image_array)
    if not vmax:
        vmax = np.amax(image_array)

    if log:
        vmin = (vmin if vmin>0 else np.amin(image_array[np.where(image_array > 0)]))
        color_norm = mpl.colors.LogNorm(vmin=vmin, vmax=vmax,clip=True)
    else:
        color_norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax,clip=True)

    ### making the plot ###
    image = axes.imshow(image_array, origin="lower", cmap=kwargs["cmap"], extent=extent, norm=color_norm)

    ### Managing the colorbar ###
    plt.colorbar(image, label=r"$\mathrm{%s} \;\left[\mathrm{%s}\right]$" % (fancy_qty(qty), kwargs["units"].latex()))
    ### Managing text ###
    # - TITLES -#
    plt.title(r"$t = \mathrm{%s\;%s},\;\;\mathrm{Quantity:\;%s}\;[\mathrm{%s}]$" % (
        np.round(snapshot.properties["time"].in_units(time_units), decimals=2),
        time_units.latex(),
        fancy_qty(qty),
        kwargs["units"].latex()), fontsize=10)
    if title:
        plt.suptitle(title, y=0.93)

    # - AXES LABELS -#
    axes.set_ylabel(r"$y\;\;\left[\mathrm{%s}\right]$" % (pyn.units.Unit(length_units).latex()))
    axes.set_xlabel(r"$x\;\;\left[\mathrm{%s}\right]$" % (pyn.units.Unit(length_units).latex()))

    # Saving
    #########################################################################################################################
    if save:
        plt.savefig(end_file)

        del image_array
        axes.cla()
        del axes
        plt.figure().clear()
        plt.clf()
        plt.close('all')
        gc.collect()
    else:
        plt.show()


# Functions for generating profiles
# ----------------------------------------------------------------------------------------------------------------------#
def make_profile_plot(snapshot,
                      qty,
                      Lambda=None,
                      Lambda_label=None,
                      profile=None,
                      save=CONFIG["Visualization"]["default_figure_save"],
                      end_file=CONFIG["system"]["directories"]["figures_directory"],
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

    if "title" in kwargs:
        title = kwargs["title"]
        del kwargs["title"]
    else:
        title = ""
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
            # - creating the profile -#
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
        y = fix_array_u(profile[qty], qty, (__quantities[qty]["unit"] if "unit_y" not in kwargs else kwargs["unit_y"]))
    except KeyError:
        make_error(ValueError, fdbg_string, "The quantity %s is not a valid quantity for this profile..." % qty)
        return None

    if qty != "temp":
        if "units_y" in kwargs:
            y = y.in_units(kwargs["units_y"])
            del kwargs["units_y"]
        else:
            y = y.in_units(__quantities[qty]["unit"])

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

    # - Finding plotting function -#
    if logx and logy:
        plt_func = plt.loglog
    elif logx:
        plt_func = plt.semilogx
    elif logy:
        plt_func = plt.semilogy
    else:
        plt_func = plt.plot

    # Plotting
    ####################################################################################################################
    # - creating the figure -#
    fig = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = fig.add_subplot(111)

    # - creating the actual plot -#
    plt_func(x, y, **kwargs, label=__quantities[qty]["fancy"])

    ##-managing the lambda function -##
    if Lambda != None:  # there is a lambda function
        plt_func(x, Lambda(x), label=(Lambda_label if Lambda_label else ""))

    # - managing text -#
    axes.set_xlabel(r"Radius [$%s$]" % (x.units.latex()))  # setting the x axis
    axes.set_ylabel(r"%s [$%s$]" % (__quantities[qty]["fancy"], y.units.latex()))
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
def generate_image_sequence(simulation_directory, qty, multiprocess=True, nproc=3, **kwargs):
    """
    Generates a sequence of images for the simulation using the given simulation and the given qty.
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
    fdbg_string = _dbg_string + "generate_image_sequence: "
    log_print("Generating %s image sequence for %s with the following kwargs: %s" % (qty, simulation_directory, kwargs),
              fdbg_string, "debug")

    # SETUP
    ########################################################################################################################
    # - File Management -#
    if not os.path.isdir(simulation_directory):  # Checking that the simulation directory exists
        make_error(OSError, fdbg_string, "The simulation directory %s doesn't appear to exist." % simulation_directory)

    ##- Getting the simulation name -##
    try:
        simulation_name = get_simulation_qty("SimulationName", {"SimulationLocation": simulation_directory})[0]
    except Exception:
        ## Something went wrong ##
        simulation_name = pt.Path(simulation_directory).name

    ##- Creating the output file set -##
    if not "av_z" in kwargs:  # We need to use av_z for the naming convention so we add it if it doesn't exist.
        kwargs["av_z"] = False

    output_directory = os.path.join(CONFIG["system"]["directories"]["figures_directory"], simulation_name,
                                    "%s-(I-%s)" % (qty, kwargs["av_z"]), datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))

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
            executor.map(mp_make_plot, arg)

    else:
        for output_direct in output_directories:  # we are plotting each of these.
            snap_number = output_direct.replace("output_", "")  # this is just the snapshot number

            # - Cleanup -#
            snapshot = pyn.load(os.path.join(simulation_directory, output_direct))

            align_snapshot(snapshot)

            # - Plotting -#
            make_plot(snapshot, qty, end_file=os.path.join(output_directory, "Image_%s.png" % snap_number), save=True,
                      **kwargs)


# Functions for generating profiles
# ----------------------------------------------------------------------------------------------------------------------#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT", level=10)
    data = pyn.load("/home/ediggins/PyCS/initial_conditions/Col_1-1_0.dat")
    data.g["smooth"] = pyn.sph.smooth(data.g)
    data.g["rho"] = pyn.sph.rho(data.g)
    make_plot(data,"temp",save=False,width="12000 kpc",cmap=plt.cm.inferno,av_z=True,resolution=500)
