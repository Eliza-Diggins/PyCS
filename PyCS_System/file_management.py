"""

    Tools for remote file management using RClone or single transfer.
-- Last Check: 12/16 --
"""
import os
import pathlib as pt
import sys

sys.path.append(str(pt.Path(os.path.realpath(__file__)).parents[1]))
from PyCS_Core.Configuration import read_config, _configuration_path
from PyCS_Core.Logging import set_log, log_print
import pathlib as pt
from concurrent.futures import ThreadPoolExecutor
from PyCS_System.text_utils import print_title, file_directory_select, rclone_file_directory_select, rclone_listdir
from tqdm import tqdm
import time
from colorama import Fore, Style
import numpy as np
import threading as t

# generating screen locking #
screen_lock = t.Semaphore(value=1) # locks off multi-threaded screen.
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------ Setup ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
_location = "PyCS_System"
_filename = pt.Path(__file__).name.replace(".py", "")
_dbg_string = "%s:%s:" % (_location, _filename)
CONFIG = read_config(_configuration_path)

# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# -------------------------------------------------- Fixed Variables ----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# - _file_header_dict is a set of all of the directories where we will find things we want to transfer.
_location_setting_names = {  # Here, we store all of the settings that we are going to look for to get diff. paths.
    "figures_directory": "Figures",
    "movies_directory": "Movies",
    "initial_conditions_directory": "Initial Conditions",
    "RAMSES_nml_directory": "NML Files"
}
_file_header_dict = {  # Stores all of the relative paths (local,box)
    CONFIG["system"]["directories"][item]: CONFIG["files"]["rclone"]["headers"][item] for item in
    _location_setting_names
}

_uploadables_dict = {  # This directory is a directory dict for use with textutils.
    _location_setting_names[key]: CONFIG["system"]["directories"][key] for key in _location_setting_names
}


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# --------------------------------------------------- Sub-Functions -----------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def get_all_files(directory, top_directory=None):
    """
    Grabs all of the files within the directory and returns as a list with (path, rel-path, file).
    Parameters
    ----------
    directory: the directory from which to search.

    Returns: Returns a list of tuples [(path,rel-path,file)].
    -------

    """
    fdbg_string = _dbg_string + "get_all_files: "
    log_print("Attempting to grab all files from directory %s." % directory, fdbg_string, "debug")

    if top_directory == None:
        top_directory = directory
    files = []  # this is the list we will eventually return.

    if not os.path.isdir(directory):
        return [(directory, str(directory).replace(top_directory, ""), "")]
    for file in os.listdir(directory):  # cycle through each directory.
        if os.path.isfile(os.path.join(directory, file)):  # this is a file, we add it.
            files.append((os.path.join(directory, file),
                          str(os.path.join(directory, file)).replace(top_directory, ""),
                          file))
        else:  # its a directory
            files += get_all_files(os.path.join(directory, file), top_directory=top_directory)

    return files


def get_all_box_files(directory, top_directory=None):
    """
    Grabs all of the files within the directory and returns as a list with (path, rel-path, file). [BOX]
    Parameters
    ----------
    directory: the directory from which to search.

    Returns: Returns a list of tuples [(path,rel-path,file)].
    -------

    """
    fdbg_string = _dbg_string + "get_all_box_files: "
    log_print("Attempting to grab all files from directory %s." % directory, fdbg_string, "debug")

    if top_directory == None:
        top_directory = directory
    files = []  # this is the list we will eventually return.

    if "." in directory:  # This is a file TODO: this is also a weak way to check.
        return [(directory, str(directory).replace(top_directory, ""), "")]
    print(rclone_listdir(directory))
    for file, status in zip(*rclone_listdir(directory)):  # cycle through each directory.
        if status:  # this is a file, we add it.
            files.append((os.path.join(directory, file),
                          str(os.path.join(directory, file)).replace(top_directory, ""),
                          file))
        else:  # its a directory
            files += get_all_box_files(os.path.join(directory, file), top_directory=top_directory)

    return files


def get_rclone_location(local_path, unfiled=CONFIG["files"]["send_to_unfiled"]):
    """
    Determines the correct path to use for rclone on the box side of file transfer.
    Parameters
    ----------
    local_path: The local path on the disk.
    unfiled: If True, then we will move items without a reasonable path to an unfiled location.

    Returns: The correct path to copy to for that file.
    -------

    """
    # setting up the debug string #
    fdbg_string = _dbg_string + "get_rclone_location:"

    ### Checking to identify the file header. ###
    if not any(local_header in local_path for local_header in list(_file_header_dict.keys())):
        # We couldn't find a header.
        log_print("Failed to find a local header for %s. Option send_to_unfiled = %s." % (local_path, unfiled),
                  fdbg_string, "error")

        ## If we have unfiled, we go to the unfiled location. Otherwise, we return false.
        if unfiled:
            ### we need to transfer to the unfiled location.
            return CONFIG["files"]["rclone"]["rclone_unfiled_directory"]  # return the unfiled directory.
        else:
            ### we aren't using unfiled.
            return False  # This indicates a failed attempt to find a path.
    else:
        ### We found a match in the headers, now we need to check all of the matches. ###
        matches = [local_header for local_header in list(_file_header_dict.keys()) if
                   local_header in local_path]  # These are the matches

        ### running through possible match lengths. ###
        if len(matches) > 1:
            log_print("Found more than 1 match for %s. Matches = %s." % (local_path, matches), fdbg_string, "warning")
            match = matches[0]
        elif not len(matches):
            log_print("Failed to find a local header for %s. Option send_to_unfiled = %s." % (local_path, unfiled),
                      fdbg_string, "error")
            return False
        else:
            match = matches[0]  # this is our actual match

    ### Manipulating the path to account for directory versus file management ###

    prop_path = str(local_path).replace(match, _file_header_dict[match])  # the proper path in box file system.

    if os.path.isfile(local_path):  # this is a file, not a directory
        return str(pt.Path(prop_path).parents[0])
    else:
        return str(local_path).replace(match, _file_header_dict[match])


def get_local_location(box_path, unfiled=CONFIG["files"]["send_to_unfiled"]):
    """
    Determines the correct path to use for rclone on the box side of file transfer.
    Parameters
    ----------
    local_path: The local path on the disk.
    unfiled: If True, then we will move items without a reasonable path to an unfiled location.

    Returns: The correct path to copy to for that file.
    -------

    """
    # setting up the debug string #
    fdbg_string = _dbg_string + "get_local_location:"

    ### Checking to identify the file header. ###
    if not any(box_header in box_path for box_header in list(_file_header_dict.values())):
        # We couldn't find a header.
        log_print("Failed to find a box header for %s. Option send_to_unfiled = %s." % (box_path, unfiled),
                  fdbg_string, "error")

        ## If we have unfiled, we go to the unfiled location. Otherwise, we return false.
        if unfiled:
            ### we need to transfer to the unfiled location.
            return CONFIG["system"]["directories"]["unfiled_directory"]  # return the unfiled directory.
        else:
            ### we aren't using unfiled.
            return False  # This indicates a failed attempt to find a path.
    else:
        ### We found a match in the headers, now we need to check all of the matches. ###
        matches = [box_header for box_header in list(_file_header_dict.values()) if
                   box_header in box_path]  # These are the matches

        ### running through possible match lengths. ###
        if len(matches) > 1:
            log_print("Found more than 1 match for %s. Matches = %s." % (box_path, matches), fdbg_string, "warning")
            match = matches[0]
        elif not len(matches):
            log_print("Failed to find a local header for %s. Option send_to_unfiled = %s." % (box_path, unfiled),
                      fdbg_string, "error")
            return False
        else:
            match = matches[0]  # this is our actual match

    ### Manipulating the path to account for directory versus file management ###
    _box_file_header_dict = {value: key for key, value in _file_header_dict.items()}
    prop_path = str(box_path).replace(match, _box_file_header_dict[match])  # the proper path in box file system.

    if "." in box_path:  # this is a file, not a directory TODO: This is a weak test for being a file.
        return str(pt.Path(prop_path).parents[0])
    else:
        return str(box_path).replace(match, _box_file_header_dict[match])


def send_item_to_rclone(location_path, unfiled=CONFIG["files"]["send_to_unfiled"]):
    """
    Sends the specified item to the correct rclone directory.
    Parameters
    ----------
    location_path: The path to the correct directory.

    Returns: None.
    -------

    """
    path = get_rclone_location(location_path, unfiled=unfiled)

    if path != False:
        # We actually found a path.
        try:
            os.system("rclone copy '%s' '%s'" % (location_path, path))
        except Exception:
            log_print("Failed to transfer %s to %s using rclone for unknown reasons..." % (location_path, path),
                      _dbg_string + "send_item_to_rclone: ", "error")
    else:
        log_print("Failed to find a reasonable path for %s. Not transfering..." % location_path,
                  _dbg_string + "send_item_to_rclone: ", "error")


def mt_send_item_to_rclone(location_path, unfiled=CONFIG["files"]["send_to_unfiled"]):
    """
    Sends the specified item to the correct rclone directory. (MULTI-Threaded)
    Parameters
    ----------
    location_path: The path to the correct directory.

    Returns: None.
    -------

    """
    t_s = time.perf_counter()
    path = get_rclone_location(location_path, unfiled=unfiled)

    if path != False:
        # We actually found a path.
        try:
            os.system("rclone copy '%s' '%s'" % (location_path, path))
        except Exception:
            log_print("Failed to transfer %s to %s using rclone for unknown reasons..." % (location_path, path),
                      _dbg_string + "send_item_to_rclone: ", "error")
    else:
        log_print("Failed to find a reasonable path for %s. Not transfering..." % location_path,
                  _dbg_string + "send_item_to_rclone: ", "error")

    t_f = str(np.round(time.perf_counter() - t_s, decimals=2))

    screen_lock.acquire()
    print(
        "%supload_files:" % _dbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: " + "Uploading %s..." % location_path + "  [%s|%s]" % (
            Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL,
            Fore.GREEN + Style.BRIGHT + "%s s" % t_f + Style.RESET_ALL
        ))
    screen_lock.release()


def get_item_from_rclone(location_path, unfiled=CONFIG["files"]["send_to_unfiled"]):
    """
    Downloads an item from box using rclone
    Parameters
    ----------
    location_path: The path to the correct directory.

    Returns: None.
    -------

    """
    path = get_local_location(location_path, unfiled=unfiled)

    if path != False:
        # We actually found a path.
        try:
            os.system("rclone copy '%s' '%s'" % (location_path, path))
        except Exception:
            log_print("Failed to transfer %s to %s using rclone for unknown reasons..." % (location_path, path),
                      _dbg_string + "get_item_from_rclone: ", "error")
    else:
        log_print("Failed to find a reasonable path for %s. Not transfering..." % location_path,
                  _dbg_string + "get_item_from_rclone: ", "error")


def mt_get_item_from_rclone(location_path, unfiled=CONFIG["files"]["send_to_unfiled"]):
    """
        Downloads an item from box using rclone. (MULTI-Threaded)
    Parameters
    ----------
    location_path: The path to the correct directory.

    Returns: None.
    -------

    """
    t_s = time.perf_counter()
    path = get_local_location(location_path, unfiled=unfiled)

    if path != False:
        # We actually found a path.
        try:
            os.system("rclone copy '%s' '%s'" % (location_path, path))
        except Exception:
            log_print("Failed to transfer %s to %s using rclone for unknown reasons..." % (location_path, path),
                      _dbg_string + "get_item_from_rclone: ", "error")
    else:
        log_print("Failed to find a reasonable path for %s. Not transferring..." % location_path,
                  _dbg_string + "get_item_from_rclone: ", "error")

    t_f = str(np.round(time.perf_counter() - t_s, decimals=2))

    screen_lock.acquire()
    print(
        "%sdownload_files:" % _dbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: " + "Downloading %s..." % location_path + "  [%s|%s]" % (
            Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL,
            Fore.GREEN + Style.BRIGHT + "%s s" % t_f + Style.RESET_ALL
        ))
    screen_lock.release()


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ----------------------------------------------------- Functions -------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
def upload_files(threaded=CONFIG["system"]["multiprocessing"]["threaded"]):
    """
    User interfaced function to allow the user to upload files and folders onto box.
    Returns:None
    -------

    """
    ### Managing introduction debugging ###
    fdbg_string = "%supload_files:" % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: "

    print("%sStarting the file uploader..." % (cdbg_string))

    ### Printing the Title ###
    print_title("PyCS (%s): File Uploader" % CONFIG["system"]["version"], "Eliza Diggins")

    time.sleep(0.1)
    print("%sStarting the file selector..." % (cdbg_string))
    ### Allowing the user to select files to upload from local disk ###
    upload_data = file_directory_select(_uploadables_dict)  # Start the file selection.

    ### Grabbing all of the necessary data ###
    if threaded:
        # We are threading
        os.system('cls' if os.name == 'nt' else 'clear')
        time.sleep(0.1)
        print_title("PyCS (%s): File Uploader" % CONFIG["system"]["version"], "Eliza Diggins")

        ## Grab the paths from selection ##
        local_file_paths = [upload_data[key]["path"] for key in upload_data]  # grab all of the paths that we selected.

        # We are threading so we need to grab --ALL-- of the files
        all_files_paths = []
        for path in local_file_paths:
            all_files_paths += get_all_files(path)

        print("%sLocated %s items in %s selected directories..." % (
            cdbg_string, len(all_files_paths), len(local_file_paths)))
        print("%sUploading %s items" % (cdbg_string, len(all_files_paths)))

        ## we only want true paths from this ##
        local_paths = [path[0] for path in all_files_paths]
        with ThreadPoolExecutor() as executor:  # start the thread pool.
            results = executor.map(mt_send_item_to_rclone, local_paths)

        print("%sFinished uploading %s items." % (cdbg_string, len(all_files_paths)))

    else:
        ### We are not using multi-threading, so we can upload each item individually.
        os.system('cls' if os.name == 'nt' else 'clear')
        time.sleep(0.1)
        print_title("PyCS (%s): File Uploader" % CONFIG["system"]["version"], "Eliza Diggins")
        local_file_paths = [upload_data[key]["path"] for key in upload_data]  # grab all of the paths that we selected.

        print("%sPreparing to upload %s items. THREADED = False." % (cdbg_string, len(local_file_paths)))

        for upload_item in tqdm(local_file_paths, desc="Uploading Files...",
                                disable=not CONFIG["system"]["logging"]["use_progress_bars"]):
            #
            #       We are now cycling through the uploads.
            #
            t_s = time.perf_counter()
            tqdm.write("%sUploading %s..." % (cdbg_string, upload_item), end="\r")
            send_item_to_rclone(upload_item)
            t_f = time.perf_counter() - t_s
            tqdm.write("%sUploading %s..." % (cdbg_string, upload_item) + "  [%s|%s]" % (
                Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL,
                Fore.GREEN + Style.BRIGHT + "%s s" % str(np.round(t_f, decimals=2)) + Style.RESET_ALL
            ))


def download_files(threaded=CONFIG["system"]["multiprocessing"]["threaded"]):
    """
    User interfaced function to allow the user to download files and folder from box.
    Returns:None
    -------

    """
    ### Managing introduction debugging ###
    fdbg_string = "%sdownload_files:" % _dbg_string
    cdbg_string = fdbg_string + " [" + Fore.LIGHTGREEN_EX + Style.BRIGHT + "FILE WIZARD" + Style.RESET_ALL + "]: "

    print("%sStarting the file downloader..." % (cdbg_string))

    ### Printing the Title ###
    print_title("PyCS (%s): File Downloader" % CONFIG["system"]["version"], "Eliza Diggins")

    time.sleep(0.1)
    print("%sStarting the file selector..." % (cdbg_string))
    ### Allowing the user to select files to download from box ###
    download_data = rclone_file_directory_select()  # Start the file selection.

    ### Grabbing all of the necessary data ###
    if threaded:
        # We are threading
        os.system('cls' if os.name == 'nt' else 'clear')
        time.sleep(0.1)
        print_title("PyCS (%s): File Downloader" % CONFIG["system"]["version"], "Eliza Diggins")

        ## Grab the paths from selection ##
        box_file_paths = [download_data[key]["path"] for key in
                          download_data]  # grab all of the paths that we selected.

        # We are threading so we need to grab --ALL-- of the files
        all_files_paths = []
        for path in box_file_paths:
            all_files_paths += get_all_box_files(path)

        print("%sLocated %s items in %s selected directories..." % (
            cdbg_string, len(all_files_paths), len(box_file_paths)))
        print("%sDownloading %s items" % (cdbg_string, len(all_files_paths)))

        ## we only want true paths from this ##
        box_paths = [path[0] for path in all_files_paths]
        with ThreadPoolExecutor() as executor:  # start the thread pool.
            results = executor.map(mt_get_item_from_rclone, box_paths)

        print("%sFinished uploading %s items." % (cdbg_string, len(all_files_paths)))

    else:
        ### We are not using multi-threading, so we can upload each item individually.
        os.system('cls' if os.name == 'nt' else 'clear')
        time.sleep(0.1)
        print_title("PyCS (%s): File Downloader" % CONFIG["system"]["version"], "Eliza Diggins")
        box_file_paths = [download_data[key]["path"] for key in
                          download_data]  # grab all of the paths that we selected.

        print("%sPreparing to download %s items. THREADED = False." % (cdbg_string, len(box_file_paths)))

        for download_item in tqdm(box_file_paths, desc="Downloading Files...",
                                  disable=not CONFIG["system"]["logging"]["use_progress_bars"]):
            #
            #       We are now cycling through the uploads.
            #
            t_s = time.perf_counter()
            tqdm.write("%sDownloading %s..." % (cdbg_string, download_item), end="\r")
            get_item_from_rclone(download_item)
            t_f = time.perf_counter() - t_s
            tqdm.write("%sDownloading %s..." % (cdbg_string, download_item) + "  [%s|%s]" % (
                Fore.CYAN + Style.BRIGHT + "DONE" + Style.RESET_ALL,
                Fore.GREEN + Style.BRIGHT + "%s s" % str(np.round(t_f, decimals=2)) + Style.RESET_ALL
            ))


# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
# ------------------------------------------------------- Main ----------------------------------------------------------#
# --|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--#
if __name__ == '__main__':
    set_log(_filename, output_type="FILE")
    download_files(threaded=True)
    # send_items_to_rclone(file_directory_select({"Initial Conditions":"/home/ediggins/PyCS"}))
