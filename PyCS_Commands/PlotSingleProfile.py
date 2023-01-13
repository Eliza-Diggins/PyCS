"""

        Command for producing a single profile of an output

"""

import os
import pathlib as pt
import sys

# adding the system path to allow us to import the important modules
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
import argparse
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
from PyCS_Analysis.Profiles import make_profile_plot
from PyCS_Analysis.Analysis_Utils import align_snapshot
from PyCS_Core.PyCS_Errors import *
import pathlib as pt
from PyCS_System.SimulationMangement import get_simulation_qty
from colorama import Fore, Style
from matplotlib.pyplot import cm
import pynbody as pyn
from datetime import datetime
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Commands"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# - managing warnings -#
if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Static Vars -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ MAIN -----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    # Argument Parsing
    ########################################################################################################################
    parser = argparse.ArgumentParser()  # setting up the command line argument parser
    #- Required args -#
    parser.add_argument("qty", help="The quantity to plot")
    parser.add_argument("ns", help="Then number of the snapshot to plot")
    #- simulation args -#
    parser.add_argument("-sim", "--simulation_name", default=None, help="The simulation name to use")
    parser.add_argument("-simdir", "--simulation_directory", default=None,
                        help="The simulation directory. Only one needs to be specified")
    #- saving -#
    parser.add_argument("-s", "--save", action="store_true", help="Use to save the image.")
    #- profile configuration kwargs -#
    parser.add_argument("-ndim","--dimensions",help="The number of dimensions to use.",default=None,type=int)
    parser.add_argument("-type","--type",help="What type to use (equaln,lin,log)",default=None)
    parser.add_argument("-nb","--nbins",help="The number of bins to use",default=None)
    parser.add_argument("-rmin","--rmin",help="The minimum radius to look at.",default=None)
    parser.add_argument("-rmax","--rmax",help="The maximum radius to look at.",default=None)
    parser.add_argument("-f", "--family", help="The family to include.", default=None)
    #- units -#
    parser.add_argument("-ux","--units_x",help="The x-units",default=None)
    parser.add_argument("-uy", "--units_y", help="The y-units", default=None)
    parser.add_argument("-tu", "--time_units", help="The time units to use in the output.",default=None)
    #- plot kwargs -#
    parser.add_argument("-t", "--title", help="The title to add to the plot.",default=None)
    parser.add_argument("-lab", "--label", help="The title to add to the plot.",default=None)
    parser.add_argument("-lx", "--logx", help="Use a logarithmic scaling on the x axis",action="store_true")
    parser.add_argument("-ly", "--logy", help="Use a logarithmic scaling on the y axis",action="store_true")
    parser.add_argument("-ls","--linestyle",help="The linestyle to use",default="-",type=str)
    parser.add_argument("-lw","--linewidth",help="The linewidth to use",default=3)
    parser.add_argument("-c", "--color", help="The color to use", default="black")
    parser.add_argument("-o", "--output_type", type=str, default="FILE", help="The type of output to use for logging.")
    parser.add_argument("-l", "--logging_level", type=int, default=10, help="The level of logging to use.")
    args = parser.parse_args()

    # Setup
    ########################################################################################################################
    set_log(_filename, output_type=args.output_type, level=args.logging_level)
    cdbg_string = Fore.CYAN + Style.BRIGHT + _dbg_string + Style.RESET_ALL + " [" + Fore.GREEN + "Command Wizard" + Style.RESET_ALL + "]"
    # ArgCHECK
    ########################################################################################################################
    #- hard sets -#
    # These kwargs are hard set because they are needed before their standard use case.
    if not args.dimensions:
        ndim = 3
    else:
        ndim = args.dimensions

    #- Directory management -#
    if not (args.simulation_name or args.simulation_directory):
        raise OSError("%s: Failed to find either -sim or -simdir. At least one is necessary..." % cdbg_string)

    if args.simulation_name:  # we were given a simulation name
        matches = get_simulation_qty("SimulationLocation", {"SimulationName": args.simulation_name})
        simulation_name = args.simulation_name
        if len(matches) == 1:
            simulation_directory = matches[0]
        elif not len(matches):
            raise SimulationBackendError("%s: Failed to find simulation %s." % (cdbg_string, args.simulation_name))
        else:
            log_print("Found more than one matching directories. Using %s." % matches[0], _dbg_string, "info")
            simulation_directory = matches[0]

    else:
        # args.simulation_directory was specified.
        simulation_directory = args.simulation_directory

        try:
            simulation_name = get_simulation_qty("SimulationName", {"SimulationLocation": args.simulation_directory})[0]
        except KeyError:
            simulation_name = pt.Path(simulation_directory).name

    # Making sure saving works
    ########################################################################################################################
    if args.save:  # we need to save
        end_file = os.path.join(CONFIG["system"]["directories"]["figures_directory"], simulation_name,
                                "%s-(ndim=%s)_Profiles" % (args.qty, ndim), datetime.now().strftime('%m-%d-%Y_%H-%M-%S'),
                                "Profile_%s.png" % args.ns)
        if not os.path.exists(pt.Path(end_file).parents[0]):
            pt.Path.mkdir(pt.Path(end_file).parents[0], parents=True)
    else:
        end_file = None

    # Running
    ########################################################################################################################
    #- load the snapshot -#
    simSnap = pyn.load(os.path.join(simulation_directory, "output_%s" % args.ns))
    simSnap = align_snapshot(simSnap)

    removable_kwargs ={ # Removable kwargs are those kwargs which need to be left out if = None
        "ndim":args.dimensions,
        "nbins":args.nbins,
        "type":args.type,
        "rmin":args.rmin,
        "rmax":args.rmax,
        "family":args.family,
        "units_x":args.units_x,
        "units_y":args.units_y,
        "time_units":args.time_units,
        "title":args.title,
        "label":args.label
    }
    kwargs = {key: value for key, value in removable_kwargs.items() if value != None}
    # PLOTTING
    ########################################################################################################################
    make_profile_plot(simSnap,args.qty,save=args.save,end_file=end_file,
                      logy=args.logy,
                              logx=args.logx,
                              ls=args.linestyle,
                              lw=args.linewidth,
                              color=args.color,**kwargs)
