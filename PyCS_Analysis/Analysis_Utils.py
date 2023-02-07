"""

        PyCS Analysis Utils for common use

"""
### Imports ###
# adding the system path to allow us to import the important modules
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
import pynbody as pyn
import numpy as np
from PyCS_Core.Logging import set_log, log_print, make_error
from PyCS_Core.PyCS_Errors import *
import warnings

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_Analysis"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

if not CONFIG["system"]["logging"]["warnings"]:
    warnings.filterwarnings('ignore')
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# - Fixed constants -#
mass_fraction = 0.6  # The standard mass fraction. This value is from Schneider (Extragalactic astronomy)
boltzmann = 1.381e-23 * pyn.units.Unit("J K^-1")
G = 6.675e-11 * pyn.units.Unit("N m^2 kg^-2")
m_p = 1.672621911e-27 * pyn.units.Unit("kg")
rho_critical = 8.5e-27 * pyn.units.Unit("kg m^-3")  # universe critical density.


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------- Multi-Processing Functions ----------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Classes --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
class SnapView:
    """
    The ``SnapView`` class is designed to allow me to interface easily with different orientations of ``pyn.snapshots.SimSnap``.

    Essentially, we use ``PyCS_Analysis.Analysis_Utils.SnapView`` as an interface by which to load snapshots from file.
    in doing so, we automatically make use of the ``align_snapshot`` functionality.
    """
    cdbg_string = "%sSnapView:" % _dbg_string

    # ----------------------------------------------------------------------------------------------------------------------#
    #      DUNDER METHODS                                                                                                  #
    # ----------------------------------------------------------------------------------------------------------------------#
    def __init__(self, view_parameters=None):
        """

        Parameters

        ----------

        view_parameters: The viewing parameters, should be ``dict`` with 2 parameters: ``angles = (az,elev)`` and ``center = (x,y,z)``. Note
        that ``center`` should ALWAYS be in the original frame of reference, not in the prime'd reference frame.
        """
        # Debugging
        # --------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%s:__init__(): " % SnapView.cdbg_string
        log_print("Generating a SnapView object with view_parameters: %s." % (view_parameters), fdbg_string, "debug")

        # Management
        # --------------------------------------------------------------------------------------------------------------#
        # setting a view parameter #

        if not view_parameters:  # There were no specified view parameters so we choose a default.
            self.vp = {
                "angles": [0,0],
                "center": pyn.array.SimArray([0,0,0],"kpc")
            }
        else:
            self.vp = view_parameters

        # - Adding additional attributes -#
        self.snapshot = None  # This stores a snapshot object if we eventually create it.


    def __setitem__(self, key, value):
        """
        Allows the user to set the new values of the ``view_parameters`` in such a way as to immediately facilitate the
        necessary rotation / centering.

        Parameters
        ----------
        key: The ``key`` value to alter, can be either ``center`` or
        value

        Returns
        -------

        """
        # Debugging
        #--------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%s__setitem__(): "%self.cdbg_string
        log_print("Changing the view parameter %s to %s."%(key,value),fdbg_string,"debug")

        # Sanitizing input
        #--------------------------------------------------------------------------------------------------------------#
        if key not in ["angles","center"]:
            make_error(KeyError,fdbg_string,"The key %s is not a valid key."%key)

        if key == "angles":
            # We are attempting to alter the angles
            #- Reversing the original angles -#
            log_print("Rotating %s -> (0,0)"%str(self.vp["angles"]),fdbg_string,"debug")

            self.snapshot.rotate_x(self.vp["angles"][1])
            self.snapshot.rotate_z(self.vp["angles"][0])

            #- Applying the new rotations -#
            log_print("Rotating (0,0) -> %s"%str(value),fdbg_string,"debug")

            self.snapshot.rotate_z(-value[0])
            self.snapshot.rotate_x(-value[1])

            self.vp["angles"] = value
        else:
            # We are attempting to alter the centering
            # Sanitize
            if isinstance(value,(list,np.ndarray,tuple)):
                value = pyn.array.SimArray(value,CONFIG["units"]["default_length_unit"])

            units = value.units

            # logging
            log_print("Centering on %s."%str(value),fdbg_string,"debug")

            # Convering to the correct coordinates #
            angles = [-np.deg2rad(val) for val in self.vp["angles"]]
            rot_matrix = np.array([[np.cos(angles[0]),-np.sin(angles[0]),0],
                                   [np.cos(angles[1])*np.sin(angles[0]),np.cos(angles[1])*np.cos(angles[0]),-np.sin(angles[1])],
                                   [np.sin(angles[1])*np.sin(angles[0]),np.sin(angles[1])*np.cos(angles[0]),np.cos(angles[1])]])
            
            value = np.matmul(rot_matrix,np.array(value).transpose())
            
            log_print("Transformed under \n%s \nmatrix (angles=%s->%s). New value is %s."%(rot_matrix,self.vp["angles"],str(angles),str(value)),fdbg_string,"debug")
            
            self.snapshot["pos"] -= pyn.array.SimArray(value,units)

            
    # -----------------------------------------------------------------------------------------------------------------#
    #     Protected Methods                                                                                            #
    # -----------------------------------------------------------------------------------------------------------------#

    # -----------------------------------------------------------------------------------------------------------------#
    #     Methods                                                                                                      #
    # -----------------------------------------------------------------------------------------------------------------#
    def load_snapshot(self,snapshot_path:str)->pyn.snapshot.SimSnap:
        """
        Aligns a RAMSES snapshot and fixes the units.
        Parameters
        ----------
        snapshot_path: The snapshot in question.

        Returns: ``pyn.snapshot.SimSnap`` object representing the loaded snap.
        -------

        """
        # Debugging
        #--------------------------------------------------------------------------------------------------------------#
        fdbg_string = "%salign_snapshot: " % self.cdbg_string
        log_print("Attempting to align RAMSES snapshot at %s." % snapshot_path, fdbg_string, "debug")

        # Loading the snapshot
        #--------------------------------------------------------------------------------------------------------------#
        snapshot = pyn.load(snapshot_path)
        self.snapshot = snapshot # grabbing a link

        # Sanitizing, Aligning, changing boxsize
        #--------------------------------------------------------------------------------------------------------------#
        #- Santizing -#
        try:
            boxlength = self.snapshot.properties[
                            "boxsize"] / 2  # This is the distance from (0,0,0) of the center of the sim box.
        except KeyError:
            raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")
        except AttributeError:
            raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")

        ##- Increasing the boxsize -##
        self.snapshot.properties["boxsize"] = 2 * self.snapshot.properties["boxsize"]

        #- Aligning -#
        self.snapshot["pos"] -= boxlength

        ##- Managing Units -##
        self.snapshot.physical_units()  # convert from raw computational units to CSG units.

        # Centering
        #--------------------------------------------------------------------------------------------------------------#
        #  IN this 1 case, we are able to center with simplicity because we do not need to worry about the
        #  orientation.
        #
        self.snapshot["pos"] -= self.vp["center"]

        log_print("Centered the snapshot at location %s."%self.vp["center"],fdbg_string,"debug")
        # Managing the View
        #--------------------------------------------------------------------------------------------------------------#
        #  REMEMBER: We are not being as careful as is possible. We apply THE Z ROTATION first, then rotate
        #            about the x-axis as we apply the elevation change.
        #
        if self.vp["angles"] != [0,0]:
            # we actually have angles to apply.
            self.snapshot.rotate_z(-self.vp["angles"][0])
            self.snapshot.rotate_x(-self.vp["angles"][1])

            log_print("Centered the snapshot on angles %s."%str(self.vp["angles"]),fdbg_string,"debug")
        else:
            pass

        log_print("Aligned %s." % self.snapshot, fdbg_string, "debug")

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# Simple sub-functions
# ----------------------------------------------------------------------------------------------------------------------#
def get_random_colors(n: int, name: str = "viridis") -> np.array:
    """
    Returns an array of HSV colors evenly distributed over n values.
    :param n: The number of values to use in the array
    :param name: The name of the colormap to use
    :return: Array containing colors.
    """
    return [plt.cm.get_cmap(name, n + 1)(i) for i in range(n)]


# SETUP Functions
# ----------------------------------------------------------------------------------------------------------------------#
def find_gas_COM(snapshot, cutoff_parameter=0.5):
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
    fdbg_string = "%sfind_gas_COM: " % _dbg_string
    log_print("Finding centers of mass for %s with cutoff parameter %s." % (snapshot, cutoff_parameter), fdbg_string,
              "debug")

    # Removing the necessary excess gas
    ####################################################################################################################
    sub = snapshot.g[pyn.filt.HighPass("rho", cutoff_parameter * np.amax(snapshot.g["rho"]))]

    # Splitting the simulation
    ####################################################################################################################
    sub1, sub2 = sub[sub["pos"][:, 0] <= 0], sub[sub["pos"][:, 0] > 0]  # split the sub into two parts.

    # Returning
    coms = (pyn.analysis.halo.center_of_mass(sub1), pyn.analysis.halo.center_of_mass(sub2))
    log_print("Identified the centers of mass to be %s and %s." % (coms[0], coms[1]), fdbg_string, "debug")
    return coms
    ####################################################################################################################


def align_snapshot(snapshot) -> None:
    """
    Aligns a RAMSES snapshot and fixes the units.
    Parameters
    ----------
    snapshot: The snapshot in question.

    Returns: None
    -------

    """
    ##- Intro debugging -##
    fdbg_string = "%salign_snapshot: " % _dbg_string
    log_print("Attempting to align RAMSES snapshot at %s." % snapshot, fdbg_string, "debug")

    ##- Grabbing the Necessary Variables -##
    try:
        boxlength = snapshot.properties[
                        "boxsize"] / 2  # This is the distance from (0,0,0) of the center of the sim box.
    except KeyError:
        raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")
    except AttributeError:
        raise IsNotRAMSESError("The simulation is not a RAMSES snapshot.")

    ##- Increasing the boxsize -##
    snapshot.properties["boxsize"] = 2 * snapshot.properties["boxsize"]

    ##- Aligning -##

    snapshot["pos"] -= boxlength

    ##- Filtering -##

    ##- Managing Units -##
    snapshot.physical_units()  # convert from raw computational units to CSG units.
    log_print("Aligned %s." % snapshot, fdbg_string, "debug")


def smooth_out(snapshot, family):
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
    fdbg_string = _dbg_string + "smooth_out: "
    log_print("Smoothing %s in snapshot %s." % (family, snapshot), fdbg_string, "warning")

    ### Grabbing the correct family ###
    fam = None  # we need to check for a real family

    for snap_fam in snapshot.families():  # iterate through each snapshot.
        if fam:
            if snap_fam.name == fam.name:  # We have a second match for the family
                log_print("Found multiple family matches for %s. Choosing %s over %s..." % (family, snap_fam.name, fam),
                          fdbg_string, "warning")
                fam = snap_fam
        else:
            if snap_fam.name == family:  # this is a first pass success
                fam = snap_fam

    if not fam:
        make_error(SnapshotError, fdbg_string, "%s is not a valid family in %s." % (family, snapshot))

    ### Running commands ###
    snapshot[fam]["smooth"] = pyn.sph.smooth(snapshot[fam])
    snapshot[fam]["rho"] = pyn.sph.rho(snapshot[fam])


def get_families(snapshot, family_names: list):
    """
    Checks the snapshot for a matching family name.
    Parameters
    ----------
    snapshot: The snapshot.
    family_names: The string for the family name.

    Returns: The correct actual family.
    -------

    """
    fdbg_string = _dbg_string + "get_family: "
    fams = []  # we need to check for a real family_name

    for snap_fam in snapshot.families():  # iterate through each snapshot.
        if snap_fam.name in family_names:
            fams.append(snap_fam)
        else:
            pass
    return fams


# PROFILE CREATION Functions
# ----------------------------------------------------------------------------------------------------------------------#
def make_pseudo_entropy(snapshot):
    """
    Produces a pseudo_entropy array for the gas in the snapshot.

    **Physics:**
    Here, we use the formula from (J. ZuHone 2018)

    S = k_b T n_e^(-2/3), following Vihklinin et al. 2006, we use n_e = rho_g/(1.252 m_p). Thus

    S = k_b T (rho_g/(1.252 m_p))^-2/3

    Parameters
    ----------
    snapshot: The snapshot to create the array for.

    Returns: None
    -------

    """
    # intro debugging
    ####################################################################################################################
    fdbg_string = "%smake_pseudo_entropy: " % _dbg_string
    log_print("Attempting to generate entropy array for %s." % snapshot, fdbg_string, "debug")

    # making correct conversions
    ####################################################################################################################
    # - constants -#
    k_b = boltzmann.in_units("keV K^-1")  # boltzmann constant
    m_p = 1.67262192369e-24  # proton mass (grams)

    # - converting units -#
    rho = snapshot.g["rho"].in_units("g cm^-3")  # converting rho to units of g/cm^3.
    temp = snapshot.g["temp"].in_units("K")  # grabbing numerical

    entropy = k_b * temp * (((rho) / (1.252 * m_p)) ** (-2 / 3))

    snapshot.g["entropy"] = entropy
    snapshot.g["entropy"].units = pyn.units.Unit("keV cm^2")


def make_mach_number(snapshot):
    """
    Generates the Mach number of the gas in the snapshot. This assumes a gamma = 5/3.

    We use the formula M = sqrt([u^2 * rho]/[gamma * p])

    Parameters
    ----------
    snapshot: The snapshot object to construct the array for.

    Returns: None
    -------

    """
    # intro debugging
    ####################################################################################################################
    fdbg_string = "%smake_mach_number: " % _dbg_string
    log_print("Attempting to generate mach number array for %s." % snapshot, fdbg_string, "debug")

    # Generating the underlying velocity
    ####################################################################################################################
    # - Comutations -#
    snapshot.g["v2"] = np.sum(snapshot.g["vel"] ** 2, axis=1)  # generates the square velocity.

    # Computing the MACH number
    ####################################################################################################################
    snapshot.g["mach"] = np.sqrt((snapshot.g["rho"] * snapshot.g["v2"]) / ((5 / 3) * snapshot.g["p"]))


def generate_xray_emissivity(snapshot) -> None:
    """
    Generates the x-ray emissivity associated with the given snapshot.

    *Note*: This is a relatively crude approach!

    - We use the full spectrum integral (6.32 in Schneider) which gives an estimate based on solar abundance.
    - e_ff = 3.0e-27 (egs cm^-3 s^-1) * sqrt(T/1K)*(n_e/1 cm^-3)^2

    Parameters
    ----------
    snapshot: The snapshot for which to produce the field.

    Returns: None
    -------

    """
    # Setup and Logging
    # ------------------------------------------------------------------------------------------------------------------#
    # - Debugging -#
    fdbg_string = "%sgenerate_xray_emissivity: " % _dbg_string
    log_print("Generating the x-ray emissivity array for snapshot %s." % (snapshot), fdbg_string, "debug")

    # - Producing the necessary computation -#
    snapshot.g["xray"] = pyn.array.SimArray(
        (3.0e-27) * np.sqrt(snapshot.g["temp"].in_units("K") / pyn.units.Unit("1 K")) * (((snapshot.g["rho"].in_units(
            "kg cm^-3") / pyn.units.Unit("kg cm^-3")) / (m_p.in_units("kg") * mass_fraction)) ** 2),
        pyn.units.Unit("erg cm^-3 s^-1"))


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
    fdbg_string = "%ssplit_binary_collision: " % _dbg_string
    log_print("Attempting to split %s." % snapshot, fdbg_string, "debug")

    # Obtaining centers of mass
    ####################################################################################################################
    centers_of_mass = find_gas_COM(snapshot, cutoff_parameter=0.001)  # calculate the centers of mass

    # Computing the annuli
    ####################################################################################################################
    diff = np.sqrt(np.sum([(centers_of_mass[0][i] - centers_of_mass[1][i]) ** 2 for i in
                           range(3)]))  # compute the difference between the two centers of mass
    filt_rad = diff / 2

    # Applying filters
    ####################################################################################################################
    snaps = [snapshot[pyn.filt.Sphere(filt_rad, cen=centers_of_mass[0])],
             snapshot[pyn.filt.Sphere(filt_rad, cen=centers_of_mass[1])]]
    # Subtracting to center
    ####################################################################################################################
    for id, snap in enumerate(snaps):
        snap["pos"] -= centers_of_mass[id]
    return snaps


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -----------------------------------------------------   MAIN   --------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="STDOUT")
    import matplotlib.pyplot as plt

    view = SnapView()
    view.load_snapshot("/home/ediggins/PyCS/RAMSES_simulations/TestSim/output_00500")
    view["angles"] = (0,90)
    view["center"] = pyn.array.SimArray([0,0,-1],"Mpc")
    make_pseudo_entropy(view.snapshot)
    print(view.snapshot.g["entropy"], view.snapshot.g["entropy"].units)
    pyn.plot.sph.image(view.snapshot.g, qty="entropy",cmap=plt.cm.jet,log=True, width="5000 kpc" )
    plt.show()
