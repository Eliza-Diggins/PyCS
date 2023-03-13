"""
Initial Condition utilities for other modules in this system.
    Eliza Diggins

"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Logging import log_print
from PyCS_Core.Configuration import _configuration_path, read_config
import struct
import numpy as np

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_InitialConditions"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------- Binary-Interaction ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def read_header(n_part:list)->str:
    """
    Generates and packs the header information for GADGET-2 type files into a set of binary packed data.

    Parameters
    ----------
    n_part: Array of number of particles present in the simulation. Format is

    [
    0: gas
    1: Halo --> DM
    2: Disk --> unused.
    3: Bulge --> unused/
    4: Stars ---> Could use if wanted.
    5: Bndry  ---> Un-used.
    ]

    Returns: The correctly packed header data.
    -------

    """
    # Introductory debugging
    # ------------------------------------------------------------------------------------------------------------------#
    fdbg_string = "%s:read_header: " % _dbg_string
    log_print("Reading header data for n_part = %s." % (n_part), fdbg_string, "debug")

    # Setup
    # ------------------------------------------------------------------------------------------------------------------#
    h_data = []  # -> Stores the eventual struct format.

    # Constructing the Struct
    # ------------------------------------------------------------------------------------------------------------------#
    # <Header Formatting>:
    # 1. Npart [6] (uint): the number of particles of each type in the simulation.
    # 2. Massarr [6] (double): The masses of each type of block -> if this is set to 0, masses are specified in the mass block.
    # 3. Time (double): Time of the output -> typically set to 0.
    # 4. Redshift (double): The starting redshift.
    # 5. FlagSfr (int): Flag for star formation.
    # 6. FlagFeedback (int)
    # 7. Nall [6] (uint): The total number of particles of each type in the entire simulation.
    # 8. FlagCooling (int):
    # 9. NumFiles (int):
    # 10. BoxSize (double): Only if periodic boundaries used.
    # 11. Omega0 (double):
    # 12. OmegaLambda (double):
    # 13. HubbleParam (double):
    # 14. FlagAge (int):
    # 15. FlagMetals (int):
    # 16. NallHw[6]
    # 17. unused filler.
    #
    # Total must be 256 bytes.
    # ------------------------------------------------------------------------------------------------------------------#
    for j in n_part:  # n_part
        h_data.append(int(j))
    for j in range(6):  # mass table
        h_data.append(0.0)
    h_data.append(0.0)  # time
    h_data.append(0.0)  # redshift
    h_data.append(0)  # flag_sfr
    h_data.append(0)  # flag_feedback
    for j in n_part:
        h_data.append(int(j))  # n_part_total
    h_data.append(0)  # flag_coooling
    h_data.append(1)  # num_files
    h_data.append(0.0)  # box_size
    h_data.append(0.0)  # omega0
    h_data.append(0.0)  # omega_lambda
    h_data.append(1.0)  # hubble_param
    h_data.append(0)  # flag_age
    h_data.append(0)  # flag_metals
    for i in np.arange(88):
        h_data.append(b'\x00')
    s = struct.Struct('iiiiii dddddd d d i i iiiiii i i dddd ii cccc\
    cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\
    cccccccccccccccccccc')

    # Returning
    # ------------------------------------------------------------------------------------------------------------------#
    packed_data = s.pack(*h_data)
    return packed_data


def write_dummy(f, values_list:list):
    """
    Writes a dummy byte sequence to the variable.
    Parameters
    ----------
    f: The file object being written into.
    values_list: A list of values to be sent to dummy integers.

    Returns: None
    -------

    """
    for i in values_list:
        dummy = [i]
        s = struct.Struct('i')
        d = s.pack(*dummy)
        f.write(d)


def write_block(f, block_data, data_type, block_name):
    """
    Writes a block of data to the given file.
    Parameters
    ----------
    f: The file
    block_data: the block data.
    data_type: the data type.
    block_name: The block name.

    Returns: None
    -------

    """
    # Setup and Debug
    # ------------------------------------------------------------------------------------------------------------------#
    fdbg_string = "%s:write_block: " % _dbg_string
    log_print("Writing block %s." % (block_name), fdbg_string, "debug")

    # Writing the block
    # ------------------------------------------------------------------------------------------------------------------#
    # Setup
    write_dummy(f, [8])
    block_name_binary = [bytes(i, 'utf-8') for i in block_name]
    f.write(struct.pack('c' * 4, *block_name_binary))

    # Determining format
    if (block_name == 'HEAD'):
        nbytes = 256  # -> Forced by format.
    else:
        fmt = data_type * len(block_data)
        nbytes = len(block_data) * 4  # -> 4 bytes for each piece of data.

    write_dummy(f, [nbytes + 8, 8, nbytes])
    if (block_name == 'HEAD'):
        f.write(block_data)
    else:
        f.write(struct.pack(fmt, *block_data))
    write_dummy(f, [nbytes])


def write_snapshot(n_part, data_list, outfile='init.dat',
                   file_format='gadget2'):
    """
    Writes the GADGET-2 data to a snapshot fil.e
    Parameters
    ----------
    n_part: The number of particles.
    data_list: The data
    outfile: The output file path.
    file_format: The file-format.

    Returns: None
    -------

    """
    # Setup and Debug
    # ------------------------------------------------------------------------------------------------------------------#
    fdbg_string = "%s:write_snapshot: " % _dbg_string
    log_print("Writing the snapshot to %s." % outfile, fdbg_string, "debug")

    # Partitioning data and setting up
    # ------------------------------------------------------------------------------------------------------------------#
    N_gas = n_part[0]  # -> Identifies the number of gas particles so we know to write U,rho, etc.

    # - fetching data types -#
    pos_data = data_list[0]
    vel_data = data_list[1]
    ID_data = data_list[2]
    mass_data = data_list[3]
    if (N_gas > 0):
        U_data = data_list[4]
        rho_data = data_list[5]
        smoothing_data = data_list[6]
    if len(data_list) > 7:
        Z = data_list[7]
    else:
        Z = False

    # Writing output
    # ------------------------------------------------------------------------------------------------------------------#
    if file_format == 'gadget2':
        # Getting the header.
        header_data = read_header(n_part)
        with open(outfile, 'wb') as f:
            write_block(f, header_data, None, 'HEAD')
            write_block(f, pos_data, 'f', 'POS ')
            write_block(f, vel_data, 'f', 'VEL ')
            write_block(f, ID_data, 'i', 'ID  ')
            write_block(f, mass_data, 'f', 'MASS')
            if (N_gas > 0):
                write_block(f, U_data, 'f', 'U   ')

                if (len(data_list) > 7):
                    write_block(f, Z, 'f', 'Z   ')

                write_block(f, rho_data, 'f', 'RHO ')
                write_block(f, smoothing_data, 'f', 'HSML')


    else:
        raise ValueError(f'{file_format} is not a supported file format.')


if __name__ == '__main__':
    pass
