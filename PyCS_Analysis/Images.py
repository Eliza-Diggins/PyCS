"""

    Functions specifically tailored for creating, manipulating, and editing simulation images.
            Written by: Eliza Diggins
"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import pathlib as pt
import sys
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import numpy as np
import scipy.ndimage
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
from PyCS_Analysis.plot_utils import get_color_binary_colormap
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Analysis.Analysis_Utils import get_families, align_snapshot, make_pseudo_entropy, make_mach_number, \
    generate_xray_emissivity, SnapView, generate_speed_of_sound
from PyCS_Core.PyCS_Errors import *
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PyCS_System.SimulationMangement import SimulationLog
from utils import split
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import current_process
import matplotlib as mpl
import gc
import warnings

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
__pynbody_image_defaults = {
    "cmap": CONFIG["Visualization"]["ColorMaps"]["default_image_colormap"],
    "resolution": CONFIG["Visualization"]["Images"]["default_resolution"],
    "width": CONFIG["Visualization"]["Images"]["default_width"]
}  # Kwargs to pass into pyn.plot.sph.image

__contour_defaults = {
    "contours": CONFIG["Visualization"]["Images"]["Contours"]["default_contours"],
    "qty": CONFIG["Visualization"]["Images"]["Contours"]["default_contour_qty"],
    "log": CONFIG["Visualization"]["Images"]["Contours"]["default_contour_log"],
    "nlevels":CONFIG["Visualization"]["Images"]["Contours"]["default_n_levels"],
    "color":CONFIG["Visualization"]["Images"]["Contours"]["default_color"],
    "legend":CONFIG["Visualization"]["Images"]["Contours"]["default_legend"],
    "av_z":CONFIG["Visualization"]["Images"]["Contours"]["projected"]
}
# ---# QUANTITY SPECIFIC DEFAULTS #-------------------------------------------------------------------------------------#
#   These dictionaries carry kwargs specific to each quantity that gets passed into either the profiles or
#   the pyn.plot.sph.image() function.
#
__quantities = {
    "vx": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "x Velocity",
        "families": ["gas", "stars", "dm"],
        "default_settings": {
            "cmap": plt.cm.seismic
        }
    },
    "vy": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "y Velocity",
        "families": ["gas", "stars", "dm"],
        "default_settings": {
            "cmap": plt.cm.seismic
        }
    },
    "vz": {
        "unit": CONFIG["units"]["default_velocity_unit"],
        "fancy": "z Velocity",
        "families": ["gas", "stars", "dm"],
        "default_settings": {
            "cmap": plt.cm.seismic
        }
    },
    "temp": {
        "unit": CONFIG["units"]["default_temperature_unit"],
        "fancy": "Temperature",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.cubehelix
        }
    },
    "rho": {
        "unit": CONFIG["units"]["default_density_unit"],
        "fancy": "Density",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.inferno,
            "log": True
        }
    },
    "p": {
        "unit": "N m^-2",
        "fancy": "Pressure",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.inferno,
            "log": True
        }
    },
    "entropy": {
        "unit": "keV cm^2",
        "fancy": "Entropy",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.jet,
            "log": True
        }
    },
    "mach": {
        "unit": "",
        "fancy": "Mach Number",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.hot
        }
    },
    "xray": {
        "unit": "erg cm^-3 s^-1",
        "fancy": r"\epsilon^{ff}",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.cividis,
            "log": True
        }
    },
    "sound_speed": {
        "unit": "km s^-1",
        "fancy": r"c_{s,\rho}",
        "families": ["gas"],
        "default_settings": {
            "cmap": plt.cm.hot,
            "log": True
        }
    }
}

# ---# PHYSICAL CONSTANTS #---------------------------------------------------------------------------------------------#
boltzmann = 1.380649e-23 * pyn.units.Unit("J K^-1")  # Defining the Boltzmann constant
critical_density = 130 * pyn.units.Unit("Msol kpc^-3")  # critical density of the universe.
critical_xray = 1e-35 * pyn.units.Unit("erg cm^-3 s^-1")


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


# Image Manipulation Functions
# ----------------------------------------------------------------------------------------------------------------------#
def merge_alpha_images(alpha_arrays: list, colors: list):
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%smerge_alpha_images: " % _dbg_string
    log_print("Merging a set of %s images." % (len(alpha_arrays)), fdbg_string, "debug")

    # SETUP
    ####################################################################################################################
    # - Are there actually arrays? -#
    if not len(alpha_arrays):
        make_error(ValueError, fdbg_string, "The set of arrays cannot be empty.")
    elif len(alpha_arrays) != len(colors):
        make_error(ValueError, fdbg_string, "The color list %s is not the same length as the arrays. (%s,%s)" % (
            colors, len(colors), len(alpha_arrays)))
    else:
        pass  # Nothing wrong

    # Generating the colormaps and normalizing the arrays
    ####################################################################################################################
    # - Make Cmaps -#
    cmaps = [mpl.colors.ListedColormap([i]) for i in colors]  # generates the correct colormaps

    # - Making the base arrays -#
    base_arrays = [cmap(array) for cmap, array in zip(cmaps, alpha_arrays)]  # grab the RBG values.

    # Combining images
    ####################################################################################################################
    # - multiplying by alphas -#
    # These are now the individual images correctly normalized.
    base_arrays = np.array(
        [base_array * np.stack([alpha_array, alpha_array, alpha_array, np.ones(alpha_array.shape)], axis=-1) for
         base_array, alpha_array in
         zip(base_arrays, alpha_arrays)])

    # - Making the image -#
    image = np.sum(base_arrays, axis=0)
    # - renormalizing -#
    image = (image / 2) * 255
    return image.astype("uint8")


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

    # Camera Management
    # ------------------------------------------------------------------------------------------------------------------#
    if "view_kwargs" in kwargs:
        view_kwargs = kwargs["view_kwargs"]
        del kwargs['view_kwargs']
    else:
        view_kwargs = None


    # MAIN
    # ------------------------------------------------------------------------------------------------------------------#
    for simulation in args[0]:  # cycle through all of the output folders.
        path = os.path.join(args[2], simulation)
        # - Aligning the snap -#
        try:
            # - Cleanup -#
            if view_kwargs:
                view = SnapView(view_parameters=view_kwargs)  # grabbing the view
                view.load_snapshot(path)
                snap = view.snapshot
                view.snapshot = None
                gc.collect()
            else:
                snap = pyn.load(path)
                align_snapshot(snap)

        except MemoryError:
            log_print("Ran out of memory", fdbg_string, "critical")
            exit()

        make_plot(snap, args[3], end_file=os.path.join(args[1], "Image_%s.png" % (simulation.replace("output_", ""))),
                  **kwargs)


def mp_make_gas_dm_plot(arg):
    """
    Multiprocessing make bary/dm plot function. The args parameter should have the format

    arg = ([simulations:list,output_directory,simulation_directory],{**kwargs})
    Parameters
    ----------
    arg: The args and kwargs for the plotting process.

    Returns: None
    -------

    """
    # Intro Debugging
    ########################################################################################################################
    fdbg_string = _dbg_string + "mp_make_gas_dm_plot: "
    log_print("Generating a multiprocessed plot with args %s. [Process: %s]" % (arg, current_process().name),
              fdbg_string, "debug")

    # Main script
    ########################################################################################################################
    args, kwargs = arg  # splitting the args and kwargs out of the tuple

    # Camera Management
    # ------------------------------------------------------------------------------------------------------------------#
    if "view_kwargs" in kwargs:
        view_kwargs = kwargs["view_kwargs"]
        del kwargs['view_kwargs']
    else:
        view_kwargs = None

    # MAIN
    # ------------------------------------------------------------------------------------------------------------------#
    for simulation in args[0]:  # cycle through all of the output folders.
        path = os.path.join(args[2], simulation)
        # - Aligning the snap -#
        try:
            # - Cleanup -#
            if view_kwargs:
                view = SnapView(view_parameters=view_kwargs)  # grabbing the view
                view.load_snapshot(path)
                snap = view.snapshot
                view.snapshot = None
                gc.collect()
            else:
                snap = pyn.load(path)
                align_snapshot(snap)

        except MemoryError:
            log_print("Ran out of memory", fdbg_string, "critical")
            exit()
        make_gas_dm_image(snap, end_file=os.path.join(args[1], "Image_%s.png" % (simulation.replace("output_", ""))),
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
        try:
            families = get_families(snapshot, __quantities[qty]["families"])
        except KeyError:
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

    # PLOTTING #
    ########################################################################################################################
    # - Generating the empty array -#
    output_array = np.zeros((kwargs["resolution"], kwargs["resolution"]))

    for family in families:
        ### Cycle through each family and generate the image array.
        # try:
        output_array += pyn.plot.sph.image(snapshot[family], qty=qty, noplot=True, **kwargs, threaded=False)
        log_print("Plotted family %s for snapshot %s and quantity %s." % (family.name, snapshot, qty),
                  fdbg_string, "info")
    # except Exception:
    #    log_print("Failed to plot family %s for snapshot %s and quantity %s." % (family.name, snapshot, qty),
    #              fdbg_string, "error")

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
    ``make_plot`` generates a plot of ``qty`` with the associated parameters.
    Parameters
    ----------
    snapshot: The snapshot to plot.
    qty: The quantity to plot.
    families: The families to include.
    save: True to save, False to show.
    end_file: The save location to use.
    time_units: The time units to display.
    title: The title of the plot.
    log: True to use log, False to use normal.
    vmin: color minimum
    vmax: color maximum.
    length_units: The length units to use for the x/y axis.
    kwargs: additional kwargs to pass.

    Returns: None
    -------

    """
    # Debugging
    #------------------------------------------------------------------------------------------------------------------#
    fdbg_string = _dbg_string + "make:plot: "
    log_print("Making plot of %s for %s." % (qty, snapshot), fdbg_string, "debug")

    # ---------------------------------------------------------------------------------------------------------------- #
    #                                   Managing kwargs passed to the function                                         #
    #    * This includes default kwargs for both the plotting procedure and for contours.                              #
    #                                                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #

    # Setting default kwargs for the MAIN plotting procedure.
    for key, value in __pynbody_image_defaults.items():  # cycle through all of the defaults
        if key not in kwargs:
            kwargs[key] = value
        else:
            pass

    # Managing the contour kwargs -> We fetch these from the kwargs and then provide defaults.
    contour_kwargs = (kwargs["contour_kwargs"].copy() if "contour_kwargs" in kwargs else {})

    ### clearing the kwargs ###
    if "contour_kwargs" in kwargs:
        del kwargs["contour_kwargs"]

    # Setting default kwargs for the Contour plotting procedure.
    for key, value in __contour_defaults.items():
        if key not in contour_kwargs:
            contour_kwargs[key] = value
        elif not contour_kwargs[key]:
            contour_kwargs[key] = value
        else:
            pass

    ### Adding additional necessary contour kwargs ###
    contour_kwargs["width"] = kwargs["width"]
    contour_kwargs["resolution"] = kwargs["resolution"]

    # - Grabbing contour information -#
    if "contours" in contour_kwargs:
        # Configuring the contour plot info
        contours = contour_kwargs["contours"] # are we generating contours or not?
        contour_qty = contour_kwargs["qty"] # The quantity to use for the contours.

        del contour_kwargs["contours"],contour_kwargs["qty"]

        # creating contour plot kwargs #
        contour_plot_kwargs = {}
        for key in ["vmin","vmax","log","levels","nlevels","color","legend"]: # these are all of the plot quantities.
            if key in contour_kwargs:
                contour_plot_kwargs[key] = contour_kwargs[key]
                del contour_kwargs[key]
            else:
                contour_plot_kwargs[key] = None
    else:
        contours = False
        contour_qty = None

    # UNIT MANAGEMENT PROCESSES #
    #---------------------------#
    if not "units" in kwargs:
        kwargs["units"] = set_units(qty)
    else:
        kwargs["units"] = pyn.units.Unit(kwargs["units"])

    if isinstance(time_units, str):
        time_units = pyn.units.Unit(time_units)


    # ---------------------------------------------------------------------------------------------------------------- #
    #                                   Managing the Actual Plotting Routines                                          #
    #                                                                                                                  #
    #                                                                                                                  #
    # ---------------------------------------------------------------------------------------------------------------- #
    ### Making the figure ###
    figure = plt.figure(figsize=tuple(CONFIG["Visualization"]["default_figure_size"]))
    axes = figure.add_subplot(111)

    # - Managing the Extends -# This allows us to set the right ticks and axes.
    numerical_width = float(pyn.units.Unit(kwargs["width"]).in_units(length_units))
    extent = [-numerical_width / 2, numerical_width / 2, -numerical_width / 2, numerical_width / 2]

    # FETCHING DATA
    #------------------------------------------------------------------------------------------------------------------#

    ##- deriving arrays -##
    qty_list = ([qty] if not contours else [qty, contour_qty]) # The quantities that we are going to need.
    if "entropy" in qty_list:
        make_pseudo_entropy(snapshot)
    if "mach" in qty_list:
        make_mach_number(snapshot)
    if "xray" in qty_list:
        generate_xray_emissivity(snapshot)
    if "sound_speed" in qty_list:
        generate_speed_of_sound(snapshot)

    # Building the base image array #
    #-------------------------------#
    image_array = generate_image_array(snapshot, qty, families=families, **kwargs)

    # Building the contour image array #
    #----------------------------------#
    if contours:
        # Managing smoothing if necessary #
        if "smoothing_kernel" in contour_kwargs:
            smoothing_kernel = contour_kwargs["smoothing_kernel"]
            del contour_kwargs["smoothing_kernel"]
        else:
            smoothing_kernel = None
        # - We need to grab the correct contour images -#
        contour_array = generate_image_array(snapshot,contour_qty,**contour_kwargs)

        if smoothing_kernel:
            contour_array = scipy.ndimage.gaussian_filter(contour_array,smoothing_kernel)
    else:
        contour_array = None

    # Aesthetic Management
    #------------------------------------------------------------------------------------------------------------------#

    # - Color management and vmin/vmax - #
    #------------------------------------#
    # Setting vmin/vmax as necessary.
    if not vmin:
        vmin = np.amin(image_array)
    if not vmax:
        vmax = np.amax(image_array)

    # managing log
    if log:
        vmin = (vmin if vmin > 0 else np.amin(image_array[np.where(image_array > 0)]))
        color_norm = mpl.colors.LogNorm(vmin=vmin, vmax=vmax, clip=True)
    else:
        color_norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax, clip=True)

    # - PLOTTING - #
    #--------------#
    image = axes.imshow(image_array, origin="lower", cmap=kwargs["cmap"], extent=extent, norm=color_norm)


    # Contour plotting procedure and management #
    #-------------------------------------------#
    print(contour_kwargs)
    if contours:
        print(contour_kwargs,contour_plot_kwargs)
        # Setting image limits #
        if not contour_plot_kwargs["vmin"]:
            contour_plot_kwargs["vmin"] = np.amin(contour_array)

        if not contour_plot_kwargs["vmax"]:
            contour_plot_kwargs["vmax"] = np.amax(contour_array)

        # Generating levels
        #--------------------------------------------------------------------------------------------------------------#
        if not contour_plot_kwargs["levels"]:
            contour_plot_kwargs["levels"] = (np.linspace(contour_plot_kwargs["vmin"],
                                                         contour_plot_kwargs["vmax"],
                                                         contour_plot_kwargs["nlevels"]) if not contour_plot_kwargs["log"] else
                                             np.logspace(np.log10(np.amax([contour_plot_kwargs["vmin"],1])),
                                                         np.log10(contour_plot_kwargs["vmax"]),
                                                         contour_plot_kwargs["nlevels"]))


        # Plotting the contours
        #--------------------------------------------------------------------------------------------------------------#
        print(contour_kwargs,contour_plot_kwargs)
        axes.contour(np.linspace(extent[0], extent[1], contour_array.shape[0]),
                     np.linspace(extent[0], extent[1], contour_array.shape[1]),
                     contour_array,
                     levels=contour_plot_kwargs["levels"],
                     colors=contour_plot_kwargs["color"])

        # Creating the contour legend
        #--------------------------------------------------------------------------------------------------------------#
        if contour_plot_kwargs["legend"]:
            # making the label
            legend_label = fancy_qty(contour_qty)

            if contour_kwargs["families"]:
                legend_label += " (%s)"%contour_kwargs["families"]

            if contour_kwargs["av_z"]:
                legend_label += " - projected"

            legend_elements = [
                Line2D([], [], color=contour_plot_kwargs["color"], label=legend_label)]

            axes.legend(handles=legend_elements,loc="upper right")


    # Colorbar Management
    #------------------------------------------------------------------------------------------------------------------#
    plt.colorbar(image, label=r"$\mathrm{%s} \;\left[\mathrm{%s}\right]$" % (fancy_qty(qty), kwargs["units"].latex()))


    # Text Management #
    #------------------------------------------------------------------------------------------------------------------#
    # - TITLES - #
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


def make_gas_dm_image(snapshot,
                      save=CONFIG["Visualization"]["default_figure_save"],
                      end_file=None,
                      vmin_dm=critical_density,
                      vmax_dm=None,
                      vmin_gas=critical_xray,
                      vmax_gas=None,
                      colors=None,
                      time_units=pyn.units.Unit(CONFIG["units"]["default_time_unit"]),
                      length_units=CONFIG["units"]["default_length_unit"],
                      **kwargs):
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%smake_gas_dm_image: " % _dbg_string
    log_print("Generating gas/dm image for snapshot %s." % snapshot, fdbg_string, "debug")

    # Setup
    ####################################################################################################################
    # - managing colors -#
    if not colors:
        colors = ["aqua", "fuchsia"]

    colors = [mpl.colors.to_rgb(i) for i in colors]

    # - Managing other settings -#
    for key, value in __pynbody_image_defaults.items():  # cycle through all of the defaults
        if key not in kwargs and key != "cmap":
            kwargs[key] = value
        else:
            pass

    if not "resolution" in kwargs:
        kwargs["resolution"] = CONFIG["Visualization"]["Images"]["default_resolution"]
    # - fetching units -#
    if not "units" in kwargs:
        unit_array = [set_units("rho"), set_units("xray")]
    else:
        unit_array = [pyn.units.Unit(kwarg) for kwarg in kwargs["units"]]
        del kwargs["units"]

    if isinstance(time_units, str):
        time_units = pyn.units.Unit(time_units)

    # Generating the plots
    ####################################################################################################################
    # building the images #
    generate_xray_emissivity(snapshot)
    dark_matter_array = generate_image_array(snapshot, "rho", families=["dm"], units=unit_array[0], **kwargs)
    baryonic_array = generate_image_array(snapshot, "xray", families=["gas"], units=unit_array[1], **kwargs)

    # - creating norms -#
    if not vmax_dm:
        vmax_dm = np.amax(dark_matter_array)  # grabbing vmins and vmaxs.
    else:
        vmax_dm = vmax_dm

    if not vmax_gas:
        vmax_gas = np.amax(baryonic_array)
    else:
        vmax_gas = vmax_gas

    # setting vmin
    ##- Recognize that if vmin is united, then we have to change to correct units. if no, leave as float.
    try:
        vmin_gas, vmin_dm = vmin_gas.in_units(unit_array[1]), vmin_dm.in_units(unit_array[0])
    except Exception:
        vmin_gas, vmin_dm = vmin_gas, vmin_dm  # we just set trivially.

    ##- Generating the norms -##
    norm_dm, norm_gas = mpl.colors.LogNorm(vmin=vmin_dm, vmax=vmax_dm, clip=True), mpl.colors.LogNorm(vmin=vmin_gas,
                                                                                                      vmax=vmax_gas,
                                                                                                      clip=True)

    # - generating the extent -#
    numerical_width = float(pyn.units.Unit(kwargs["width"]).in_units(length_units))
    extent = [-numerical_width / 2, numerical_width / 2, -numerical_width / 2, numerical_width / 2]
    # Generating the images
    ####################################################################################################################

    final_image = merge_alpha_images([norm_gas(baryonic_array), norm_dm(dark_matter_array)], colors)
    # - cleaning up -#
    del baryonic_array, dark_matter_array
    gc.collect()
    # Plotting
    ####################################################################################################################
    # - Figure settings -#
    l = 8  # the size of the actual image in inches
    a1, a2, b1, b2 = (0.1, 0.03, 0.1, 0.1)  # these are the subplot margins
    w, h = l / ((0.74) * (1 - (a1 + a2))), l / (1 - (b1 + b2))
    axis_ratio = h / w
    # - Making the figure -#
    fig = plt.figure(figsize=(8, 8 * axis_ratio))
    axes = fig.add_subplot(111)

    axes.imshow(final_image, extent=extent)

    # - TITLES -#
    plt.title("Comparative Distribution of Dark Matter and Baryonic Matter\n" + r"$t = \mathrm{%s\;%s}$" % (
        np.round(snapshot.properties["time"].in_units(time_units), decimals=2),
        time_units.latex()), fontsize=10)

    # - AXES LABELS -#
    axes.set_ylabel(r"$y\;\;\left[\mathrm{%s}\right]$" % (pyn.units.Unit(length_units).latex()))
    axes.set_xlabel(r"$x\;\;\left[\mathrm{%s}\right]$" % (pyn.units.Unit(length_units).latex()))
    axes.set_facecolor("black")

    # - Adding colorbars -#

    ##- Fetching the necessary colormaps -##
    cmap_gas, cmap_dm = tuple([get_color_binary_colormap(col) for col in colors])  # grabs the correct colormaps

    # creating the mapables #
    bar_gas, bar_dm = plt.cm.ScalarMappable(norm=norm_gas, cmap=cmap_gas), plt.cm.ScalarMappable(norm=norm_dm,
                                                                                                 cmap=cmap_dm)
    plt.colorbar(bar_gas, label=r"X-ray Emissivity / $%s$" % unit_array[1].latex(), fraction=0.1, pad=0.05)
    plt.colorbar(bar_dm, label=r"Dark Matter Density / $%s$" % unit_array[0].latex(), fraction=0.1, pad=0.01)

    # - adjusting subplots -#
    plt.subplots_adjust(left=a1, right=1 - a2, bottom=b1, top=1 - b2)
    # - saving -#
    if save:
        plt.savefig(end_file)

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
        simulation_name = simlog.match("SimulationLocation", "SimulationName", simulation_directory)[0]
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
        # CAMERA MANAGEMENT
        # ------------------------------------------------------------------------------------------------------------------#
        if "view_kwargs" in kwargs:
            view_kwargs = kwargs["view_kwargs"]
            del kwargs["view_kwargs"]
        else:
            view_kwargs = None

        # Running
        # --------------------------------------------------------------------------------------------------------------#
        for output_direct in output_directories:  # we are plotting each of these.
            snap_number = output_direct.replace("output_", "")  # this is just the snapshot number

            # - Cleanup -#
            if view_kwargs:
                view = SnapView(view_parameters=view_kwargs)  # grabbing the view
                view.load_snapshot(os.path.join(simulation_directory, output_direct))
                snapshot = view.snapshot
                view.snapshot = None
                gc.collect()
            else:
                snapshot = pyn.load(os.path.join(simulation_directory, output_direct))
                align_snapshot(snapshot)

            # - Plotting -#
            make_plot(snapshot, qty, end_file=os.path.join(output_directory, "Image_%s.png" % snap_number), save=True,
                      **kwargs)


def generate_dm_baryon_image_sequence(simulation_directory, multiprocess=True, nproc=3, **kwargs):
    """
    Generates a sequence of baryon/dm images for the simulation using the given simulation.
    Parameters
    ----------
    simulation_directory: The location of the simulation datafiles.
    kwargs: The additional kwargs to pass to the plotting system.

    Returns
    -------

    """
    # DEBUGGING
    ########################################################################################################################
    fdbg_string = _dbg_string + "generate_dm_baryon_image_sequence: "
    log_print(
        "Generating dm/baryon image sequence for %s with the following kwargs: %s" % (simulation_directory, kwargs),
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

    ##- Creating the output file set -##
    if not "av_z" in kwargs:  # We need to use av_z for the naming convention so we add it if it doesn't exist.
        kwargs["av_z"] = False

    output_directory = os.path.join(CONFIG["system"]["directories"]["figures_directory"], simulation_name,
                                    "%s-(I-%s)" % ("DM-B", kwargs["av_z"]),
                                    datetime.now().strftime('%m-%d-%Y_%H-%M-%S'))

    if not os.path.exists(output_directory):
        pt.Path.mkdir(pt.Path(output_directory), parents=True)
    ##- Debugging -##
    log_print("Saving figures to %s." % (output_directory), fdbg_string, "debug")

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

        arg = [([partition[i], output_directory, simulation_directory], kwargs) for i in range(len(partition))]
        with ProcessPoolExecutor() as executor:
            executor.map(mp_make_gas_dm_plot, arg)

    else:
        # CAMERA MANAGEMENT
        # ------------------------------------------------------------------------------------------------------------------#
        if "view_kwargs" in kwargs:
            view_kwargs = kwargs["view_kwargs"]
            del kwargs["view_kwargs"]
        else:
            view_kwargs = None

        # Running
        # --------------------------------------------------------------------------------------------------------------#
        for output_direct in output_directories:  # we are plotting each of these.
            snap_number = output_direct.replace("output_", "")  # this is just the snapshot number
            # - Cleanup -#
            if view_kwargs:
                view = SnapView(view_parameters=view_kwargs)  # grabbing the view
                view.load_snapshot(os.path.join(simulation_directory, output_direct))
                snapshot = view.snapshot
                view.snapshot = None
                gc.collect()
            else:
                snapshot = pyn.load(os.path.join(simulation_directory, output_direct))
                align_snapshot(snapshot)

            # - Plotting -#
            make_gas_dm_image(snapshot, end_file=os.path.join(output_directory, "Image_%s.png" % snap_number),
                              save=True,
                              **kwargs)


# Functions for generating profiles
# ----------------------------------------------------------------------------------------------------------------------#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT", level=10)
    data = pyn.load('/home/ediggins/PyCS/RAMSES_simulations/TestSim/output_00500')
    align_snapshot(data)

    make_plot(data, "rho",families="gas",log=True, save=False, contour_kwargs={"contours":True,
                                                        "log":True,
                                                        "nlevels":10,
                                                        "qty":"rho",
                                                        "families":"dm",
                                                        "av_z":True,
                                                        "smoothing_kernel":10})
    plt.show()
