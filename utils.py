import os
import re
import signal
import subprocess


class Result:
    """Class of result attributes of an executed command."""
    def __init__(self, command, stdout, stderr, pid, exit_status):
        """Initializes a Result instance with command execution details.

        Args:
            command: command to be executed.
            exit_status: command's exit status.
            stdout: command's output.
            stderr: command's error.
            pid: Process ID of the executed command.
        """
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.pid = pid
        self.exit_status = exit_status

    def __repr__(self):
        """Returns a string representation of the Result object for debugging.

        Returns:
            A string showing the command, stdout, stderr, and exit status of the Result object.
        """
        return f"Result(command = {self.command!r}, stdout = {self.stdout!r}, stderr = {self.stderr!r}, exit_status = {self.exit_status!r})"


def run(log, command, logfile=None, subprocess_data="", block=True):
    """Executes a command in a subprocess and returns its process id, output,
    error and exit status.

    This function will block until the subprocess finishes or times out.

    Args:
        log: logger instance for capturing logs
        command: command to be executed.
        logfile: command output logfile path.
        subprocess_data: Input to be given for the subprocess.

    Returns:
        result: result object of executed command.
    """
    if not block:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc
    if logfile:
        proc = subprocess.Popen(command, stdout=open(logfile, 'w+'), stderr=open(logfile, 'w+'), stdin=subprocess.PIPE,
                                shell=True)
        return proc
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)

    (out, err) = proc.communicate(timeout=600, input=subprocess_data.encode())

    result = Result(command=command, stdout=out.decode("utf-8").strip(), stderr=err.decode("utf-8").strip(),
                    pid=proc.pid, exit_status=proc.returncode)
    output = out.decode("utf-8").strip() if out else err.decode("utf-8").strip()
    log.info("Command : %s\nOutput : %s", command, output)
    return result


def get_controllers_connected(log):
    """Returns the list of controllers connected to the host.

    Args:
        log: Logger object for info logging.

    Returns:
        controller_list: Dictionary with BD address as key and interface as value.
    """
    controllers_list = {}
    result = run(log, 'hciconfig -a | grep -B 2 \"BD A\"')
    result = result.stdout.split("--")
    if result[0]:
        for res in result:
            res = res.strip("\n").replace('\n', '')
            if match := re.match('(.*):	Type:.+BD Address: (.*) ACL(.*)', res):
                controllers_list[match[2]] = match[1]
        log.info("Controllers %s found on host", controllers_list)
    return controllers_list


def start_dump_logs(interface, log, log_path):
    """Starts the hcidump logging process, if running.

      Args:
          interface: The Bluetooth interface to stop logging for.
          log: Logger instance used for logging.
          log_path: log file path.
      Returns:
           Full path to the log file if the `hcidump` process was successfully started.
          False if the process fails to start or if the interface is not provided.
      """
    try:
        if not interface:
            log.error("Interface is not provided for hcidump")
            return
        stop_dump_logs(log)
        subprocess.run(["hciconfig", interface, "up"])
        hcidump_log_name = os.path.join(log_path, f"{interface}_hcidump.log")
        log.info("Starting hcidump...")
        hcidump_command = "/usr/local/bluez/bluez-tools/bin/hcidump"
        subprocess.Popen(
            [hcidump_command, "-i", interface, "-Xt"],
            stdout=open(hcidump_log_name, 'a+'),
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        log.info("hcidump process started:%s", hcidump_log_name)
        return hcidump_log_name
    except Exception as e:
        log.error("[Failed to start hcidump:%s", e)
        return False

'''def start_dump_logs(interface, log, log_path):
    """Starts the hcidump logging process if not already running with correct log path."""
    try:
        if not interface:
            log.error("Interface is not provided for hcidump")
            return False
        expected_log_file = os.path.join(log_path, f"{interface}_hcidump.log")
        hcidump_command = "/usr/local/bluez/bluez-tools/bin/hcidump"
        existing_pid = None
        ps_output = subprocess.check_output(["ps", "-eo", "pid,args"], text=True)
        for line in ps_output.splitlines():
            if f"{hcidump_command} -i {interface} -Xt" in line:
                existing_pid = int(line.strip().split(None, 1)[0])
                log.info(f"hcidump already running for interface {interface} with PID {existing_pid}")
                try:
                    lsof_output = subprocess.check_output(["lsof", "-p", str(existing_pid)], text=True)
                    if expected_log_file in lsof_output:
                        log.info(f"hcidump is already logging to expected file: {expected_log_file}")
                        return expected_log_file
                    else:
                        log.warning(f"hcidump is running but logging to unexpected file. Restarting...")
                        os.kill(existing_pid, signal.SIGTERM)
                        break
                except Exception as e:
                    log.warning(f"Failed to inspect running hcidump (PID {existing_pid}): {e}")
                    os.kill(existing_pid, signal.SIGTERM)
                    break
        subprocess.run(["hciconfig", interface, "up"])
        log.info("Starting hcidump...")
        with open(expected_log_file, 'a+') as log_file:
            subprocess.Popen(
                [hcidump_command, "-i", interface, "-Xt"],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )
        log.info("[INFO] hcidump process started: %s", expected_log_file)
        return expected_log_file
    except Exception as e:
        log.error("Failed to start hcidump: %s", e)
        return False'''

def stop_dump_logs(log):
    """Stops the hcidump logging process, if running.

    Args:
        log: Logger instance used for logging messages.
    Returns:
        True if the process was stopped or not running.
    """
    log.info("Stopping HCI dump logs")
    hcidump_cmd = "killall -9 /usr/local/bluez/bluez-tools/bin/hcidump"
    run(log=log, command=hcidump_cmd)
    log.info("HCI dump logs stopped successfully")


def get_controller_interface_details(log, interface, detail_level=None):
    """Retrieves Bluetooth controller details for the specified interface.

    Args:
        log: Logger instance for logging command output.
        interface: Bluetooth interface name (e.g., 'hci0').
        detail_level: Either 'basic_info' or 'extended_info'.
    Returns:
        A string or dictionary containing the controller details,depending on the detail_level
    """
    result = run(log, f"hciconfig -a {interface}")
    output = result.stdout
    bus_match = re.search(r'Bus: (\w+)', output)
    bus_type = bus_match.group(1) if bus_match else 'Unknown'
    if detail_level == 'basic_info':
        return f"Interface: {interface}\tBus: {bus_type}"
    elif detail_level != 'extended_info':
        raise ValueError(f"Invalid detail_level : '{detail_level}'. Use 'basic_info' or 'extended_info'.")
    patterns = {
    'Name': (r"Name:\s*'(.+?)'", 'Unknown'),
    'BD_ADDR': (r'BD Address: ([0-9A-F:]+)', 'Unknown'),
    'Link mode': (r'Link mode: (.+)', 'Unknown'),
    'Link policy': (r'Link policy: (.+)', 'Unknown'),
    'HCI Version': (r'HCI Version:\s*([^\s]+ \([^)]+\))', 'Unknown'),
    'LMP Version': (r'LMP Version:\s*([^\s]+ \([^)]+\))', 'Unknown'),
    'Manufacturer': (r'Manufacturer: (.+)', 'Unknown'),}
    controller_details ={}
    for key, (pattern, default) in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        controller_details[key] = match.group(1).strip() if match else default
    return controller_details


def controller_enable(log, interface):
    """Brings the specified controller interface up.

    Args:
        log: Logger instance.
        interface: Name of the controller interface.
    """
    run(log, f"hciconfig -a {interface} up")
    log.info("Controller %s brought up.", interface)


def stop_daemons(log):
    """Stops all running daemon processes."""
    log.info("Stopping all running daemons...")
    command = "killall -9 /usr/local/bluez/dbus-1.12.20/bin/dbus-daemon"
    run(log=log, command=command)
    run(log=log, command = "killall -9 /usr/lib/bluetooth/obexd")
    log.info("Successfully stopped daemon processes.")


def start_dbus_daemon(log):
    """Starts the D-Bus daemon."""
    log.info("Cleaning up existing D-Bus daemons...")
    stop_daemons(log)
    log.info("Starting D-Bus daemon...")
    command = "/usr/local/bluez/dbus-1.12.20/bin/dbus-daemon --system --nopidfile"
    run(log=log, command=command)
    log.info("D-Bus daemon started successfully.")

def start_bluetooth_daemon(log):
    """Starts the bluetooth daemon and begins logging its output."""
    log.info("Cleaning up existing bluetooth daemons...")
    bluetoothd_log_name = os.path.join(log.log_path, "bluetoothd.log")
    log.info("Starting bluetooth daemon...")
    command = "/usr/local/bluez/bluez-tools/libexec/bluetooth/bluetoothd -nd --compat"
    run(log=log, command=command, logfile=bluetoothd_log_name)
    log.info("Bluetoothd logs started %s", bluetoothd_log_name)


def start_pulseaudio_daemon(log):
    """Starts the pulseaudio daemon and begins logging its output."""
    log.info("Cleaning up existing pulseaudio daemons...")
    stop_pulseaudio_daemon(log)
    pulseaudio_log_name = os.path.join(log.log_path, "pulseaudio.log")
    log.info("Starting pulseaudio daemon...")
    command = "/usr/local/bluez/pulseaudio-13.0_for_bluez-5.65/bin/pulseaudio -vvv"
    run(log=log, command=command, logfile=pulseaudio_log_name)
    log.info("pulseaudio logs started %s", pulseaudio_log_name)


def stop_pulseaudio_daemon(log):
    log.info("Stopping pulseaudio daemon...")
    run(log=log, command="pkill -9 -f pulseaudio")
    log.info("Pulseaudio daemon stopped.")
