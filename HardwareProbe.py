#!/usr/bin/env python
from subprocess import PIPE, Popen
from pathlib import Path
import psutil
import time
import os
import platform
import re

def get_is_reboot_required():
    """
    Linux specific check to see if a server reboot is required. It does this by checking if the file
    "/var/run/reboot-required" exists in the system.
    """
    is_reboot_required = Path("/var/run/reboot-required")
    if is_reboot_required.is_file():
        # File exits and reboot is required:
        return True
    else:
        return False

def get_amount_of_updates_available():
    """
    Linux specific check to get the amount of available updates for the system. This requires the package
    'apt install update-notifier-common' to be installed, by default this is installed in Ubuntu systems.
    """

    # ?: Do the folder '/usr/lib/update-notifier' exist in the system
    update_notifier_directory = Path("/usr/lib/update-notifier")
    if update_notifier_directory.is_dir():
        # -> Yes it exists so call the '/usr/lib/update-notifier/apt-check --human-readable'
        process = Popen(['/usr/lib/update-notifier/apt-check', '--human-readable'], stdout=PIPE)
        output, _error = process.communicate()

        # The human-readable outputs to lines, first has the amount of normal packages needing updates
        # second has the amount of security updates needing updates.
        byte_array = output.split(b'\n')

        # E-> got what we need so get the amount of packages and security that can be upgraded.
        package_updates = re.sub(r'\D', "", byte_array[0].decode())
        security_updates = re.sub(r'\D', "", byte_array[1].decode())
        status = {'security_packages': security_updates, 'packages_updates': package_updates}
        return status
    else:
        # E-> No, folder does not exits.
        return None

def get_rpi_cpu_temperature():
    """Raspberry pi specific cpu temp sensor. Uses a Raspbbery batch command to get the temperature.
    This vcgencmd command returns [temp=42.9'C] and is then processed by python to return the number in
    that string."""
    try:
        # This command gives the result: [temp=42.9'C]
        process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
        output, _error = process.communicate()
        # Get the to get the temp start from the char = ands top at ' 1: is python way and means starting index. this ads the = location +1 and sets end index to '
        # python2 only    print(output[output.index('=') + 1:output.rindex("'")])
        return float(output[output.index('='.encode()) + 1:output.rindex("'".encode())])
    except OSError:
        print("vsgencmd not fount! This is Raspberry pi only command")
        return None


def get_cpu_percent():
    """Return the cpu used as an percent. this uses the linux batch command mpstat. Python is
    then used to get the last word in the result string. This last word contains the pecent free and
    is then used to calculate the amount used."""
    try:
        process = Popen(['mpstat'], stdout=PIPE)
        output, _error = process.communicate()
        # Last word in the output string is the percent free.
        freePercent = output.split()[-1]
        # But we want used cpu amount not free so subtract from 100%
        return round(100.0 - float(freePercent), 2)
    except OSError:
        print("mpstat not found, please check if it's installed!")
        return None


def get_active_users_processes():
    """Return the amount of active users (all users) processes as an integer. This uses
    batch shell to process the result"""
    try:
        # the shell=true should never be used with user inputs!
        process = Popen(['ps axue | grep -vE "^USER|grep|ps" | wc -l'], shell=True, stdout=PIPE)
        output, _error = process.communicate()
        return int(output)
    except OSError:
        print("Unable to run [ps axue | grep -vE \"^USER|grep|ps\" | wc -l]!")
        return None

def getLoad():
    """Get the system load in 1m,5m and 10m. This is available under Linux or Darwin only."""
    load = {}
    system_load = os.getloadavg()
    # check if system_load is None before adding it
    if system_load is not None:
        # In this tupple get the middle one
        load.update({"1m": round(system_load[0], 2)})
        load.update({"5m": round(system_load[1], 2)})
        load.update({"10m": round(system_load[2], 2)})
        return load

def getProbeReport(diskUsageFromPaths=["."], isRaspberryPi=False):
    """Retrieve a dictionary that contains the server status. Depending on the os used will contain the rpi cpu temp if
    running on a Raspberry pi, cpu percent if running in linux and active user processes if running on linux or
    darwin (osx)
    :param drives - list containing the drives to get the disk usage for. Default to the drive this
    script is running on."""

    # This dictonary will be used to contain all the server stats:
    serverStatus = {}

    # :: Following commands is only available in linux
    if platform.system() == "Linux":
        cpu_usage = get_cpu_percent()
        # Got used cpu percent, but check if it is None before adding it
        if cpu_usage is not None:
            serverStatus.update({'cpu_usage': cpu_usage})

        # Check if the system needs reboot:
        is_reboot_required = "Yes" if get_is_reboot_required() else "No"
        serverStatus.update({'reboot_required': is_reboot_required})

        # Check if we can include the needed security updates:
        updates_available = get_amount_of_updates_available()
        # ?: Did we get the amount of updates needing update
        if updates_available is not None:
            # -> Yes, include it to the dict
            serverStatus.update({'updates': updates_available})

    # :: Following commands is only available in linux or osx (Darwin)
    if platform.system() == "Linux" or "Darwin":
        system_load = getLoad()
        if system_load is not None:
            serverStatus.update({'load': system_load})

        active_users_processes = get_active_users_processes()
        # Got number of active processes:
        serverStatus.update({'users_processes': active_users_processes})


    # :: This is only available in a raspberry pi
    if isRaspberryPi:
        rpi_cpu_temp = get_rpi_cpu_temperature()
        # check if rpi_cpu_temp is None before adding it
        if rpi_cpu_temp is not None:
            serverStatus.update({'rpi_cpu_tmp': rpi_cpu_temp})

    # Next section is available in all systems:
    serverStatus.update({'ram': psutil.virtual_memory()})

    # Get percent used on current disk this script is running on
    diskUsages = {}
    for path in diskUsageFromPaths:
        # Get all the drives we should get the disk usage for:
        diskUsages.update({path : psutil.disk_usage(path)})
    serverStatus.update({'disk': diskUsages})

    # Get the amount of swap used:
    serverStatus.update({'swap': psutil.swap_memory()})

    # Get uptime in seconds
    upTimeInSeconds = int(time.time()) - psutil.boot_time()
    serverStatus.update({'uptime': int(upTimeInSeconds)})

    # Amount of active users, due to one user can have multiple terminals we should handle this by
    # checking unique names.
    users = psutil.users()
    userNames = []
    for user in users:
        if user.name not in userNames:
            # We do not have this username yet. add it
            userNames.append(user.name)
    serverStatus.update({'users': len(userNames)})

    # Try to get the temp sensors from the system. This may not work on some python versions and
    # other hardware may have no sensors.
    try:
        tempSensors = psutil.sensors_temperatures()
        if len(tempSensors) > 0:
            # Has some sensors to show.. add them
            serverStatus.update({'temp_sensors': tempSensors})
    except AttributeError:
        print("Unable to get sensors_temperatures")

    # Try to get fan information. from the system. This may not work on some python versions and
    # other hardware may have no sensors.
    try:
        tempSensors = psutil.sensors_fans()
        if len(tempSensors) > 0:
            # Has some sensors to show.. add them
            serverStatus.update({'fan_sensors': tempSensors})
    except AttributeError:
        print("Unable to get sensors_fans")

    return serverStatus

