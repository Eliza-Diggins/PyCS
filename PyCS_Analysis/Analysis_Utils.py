"""

        PyCS Analysis Utils for common use

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import sys
import pathlib as pt
sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
import numpy as np
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Core.PyCS_Errors import *
import toml
from datetime import datetime
from colorama import Fore, Back, Style

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def find_gas_COM(snapshot,cutoff_parameter=0.5):
    """
    Finds the centers of mass of a colliding cluster.

    **Algorithm**

    - To identify the center of mass, we split the cluster down the middle, separating x<0, x>= 0.
    - We then reduce the gas mass by the ``cutoff_parameter`` and look for the separated centers of mass.
    Parameters
    ----------
    snapshot: The snapshot to split in order to identify the center of mass.
    cutoff_parameter: float, the characteristic cutoff used to identify the COM, percentage of maximal density.

    Returns: the center of mass positions of the two clusters.
    -------

    """
    # Intro Debugging
    ####################################################################################################################
    fdbg_string = "%sfind_gas_COM: "%_dbg_string
    log_print("Finding centers of mass for %s with cutoff parameter %s."%(snapshot,cutoff_parameter),fdbg_string,"debug")

    # Removing the necessary excess gas
    ####################################################################################################################
    sub = snapshot.g[pyn.filt.HighPass("rho",cutoff_parameter*np.amax(snapshot.g["rho"]))]

    # Splitting the simulation
    ####################################################################################################################
    sub1,sub2 = sub[sub["pos"][:,0] <=0],sub[sub["pos"][:,0] > 0] # split the sub into two parts.

    # Returning
    coms = (pyn.analysis.halo.center_of_mass(sub1),pyn.analysis.halo.center_of_mass(sub2))
    log_print("Identified the centers of mass to be %s and %s."%(coms[0],coms[1]),fdbg_string,"debug")
    return coms
    ####################################################################################################################
def align_snapshot(snapshot)->None:
    """
    Aligns a RAMSES snapshot and fixes the units.
    Parameters
    ----------
    snapshot: The snapshot in question.

    Returns: None
    -------

    """
    ##- Intro debugging -##
    fdbg_string = "%salign_snapshot: "%_dbg_string
    log_print("Attempting to align RAMSES snapshot at %s."%snapshot,fdbg_string,"debug")

    ##- Grabbing the Necessary Variables -##
    try:
        boxlength = snapshot.properties["boxsize"]/2 # This is the distance from (0,0,0) of the center of the sim box.
    except KeyError:
        raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")
    except AttributeError:
        raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")

    ##- Aligning -##

    snapshot["pos"] -= boxlength

    ##- Managing Units -##
    snapshot.physical_units() # convert from raw computational units to CSG units.
    log_print("Aligned %s."%snapshot,fdbg_string,"debug")

def smooth_out(snapshot,family):
    """
    Uses the built in functions pyn.sph.smooth and pyn.sph.rho to compute sph values for non-sph families.

    -- THIS SHOULD BE USED CAUTIOUSLY --
    Parameters
    ----------
    snapshot: The snapshot to use.
    family: The family to smooth.

    Returns: None
    -------

    """
    fdbg_string = _dbg_string+"smooth_out: "
    log_print("Smoothing %s in snapshot %s."%(family,snapshot),fdbg_string,"warning")

    ### Grabbing the correct family ###
    fam = None # we need to check for a real family

    for snap_fam in snapshot.families(): # iterate through each snapshot.
        if fam:
            if snap_fam.name == fam.name: # We have a second match for the family
                log_print("Found multiple family matches for %s. Choosing %s over %s..."%(family,snap_fam.name,fam),fdbg_string,"warning")
                fam = snap_fam
        else:
            if snap_fam.name == family: # this is a first pass success
                fam = snap_fam

    if not fam:
        make_error(SnapshotError,fdbg_string,"%s is not a valid family in %s."%(family,snapshot))

    ### Running commands ###
    data[fam]["smooth"] = pyn.sph.smooth(data[fam])
    data[fam]["rho"] = pyn.sph.rho(data[fam])

def get_families(snapshot,family_names:list):
    """
    Checks the snapshot for a matching family name.
    Parameters
    ----------
    snapshot: The snapshot.
    family_names: The string for the family name.

    Returns: The correct actual family.
    -------

    """
    fdbg_string = _dbg_string+"get_family: "
    fams = [] # we need to check for a real family_name

    for snap_fam in snapshot.families(): # iterate through each snapshot.
        if snap_fam.name in family_names:
            fams.append(snap_fam)
        else:
            pass
    return fams
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def split_binary_collision(snapshot):
    """
    This function splits a binary collision in the x-y plane into the two component sub clusters.

    *Prerequisites:* Must already be smooth and aligned with physical units.

    **Limitations:**

    - This is only viable while the clusters are still largely separated. If they are no longer separated, then some of the baryonic mass which composes the cluster will be lost to the calculation.
    - We can only see at most a ring of half COM distance around each central over density.

    **Algorithm:**

    - We first identify the center of mass of each of the component clusters by splitting the simulation along x=0 and then constraining ourselves to identify only the highest mass regions.

    - We then use an annulus of half COM difference to isolate each cluster and center.
    Parameters
    ----------
    snapshot: The snapshot to split

    Returns: Two snapshots, each representing a single constituent cluster.
    -------

    """
    # Intro debugging
    ####################################################################################################################
    fdbg_string = "%ssplit_binary_collision: "%_dbg_string
    log_print("Attempting to split %s."%snapshot,fdbg_string,"debug")

    # Obtaining centers of mass
    ####################################################################################################################
    centers_of_mass = find_gas_COM(snapshot,cutoff_parameter=0.001) # calculate the centers of mass

    # Computing the annuli
    ####################################################################################################################
    diff = np.sqrt(np.sum([(centers_of_mass[0][i]-centers_of_mass[1][i])**2 for i in range(3)])) # compute the difference between the two centers of mass
    filt_rad = diff/2

    # Applying filters
    ####################################################################################################################
    snaps =  [snapshot[pyn.filt.Sphere(filt_rad,cen=centers_of_mass[0])],
            snapshot[pyn.filt.Sphere(filt_rad,cen=centers_of_mass[1])]]
    # Subtracting to center
    ####################################################################################################################
    for id,snap in enumerate(snaps):
        snap["pos"] -= centers_of_mass[id]
    return snaps
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename,output_type="STDOUT")
    import matplotlib.pyplot as plt
    data = pyn.load("/home/ediggins/PyCS/initial_conditions/Col_1-1_0.dat")
    data.g["smooth"] = pyn.sph.smooth(data.g)
    data.g["rho"] = pyn.sph.rho(data.g)
    dat = split_binary_collision(data)
    pyn.plot.sph.image(dat[0].g,width="12000 kpc")
    plt.show()

