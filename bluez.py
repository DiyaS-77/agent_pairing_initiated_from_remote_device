import dbus
import dbus.mainloop.glib
import dbus.service
import os
import subprocess
import time
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from libraries.bluetooth import constants
from Utils.utils import run

class BluetoothDeviceManager:
    """A class for managing Bluetooth devices using the BlueZ D-Bus API."""

    def __init__(self, log=None, interface=None):
        """Initialize the BluetoothDeviceManager by setting up the system bus and adapter.

        Args:
            log: Logger instance.
            interface: Bluetooth adapter interface (e.g., hci0).
        """
        self.bus = dbus.SystemBus()
        self.interface = interface
        self.log = log
        self.adapter_path = f'{constants.bluez_path}/{self.interface}'
        self.adapter_proxy = self.bus.get_object(constants.bluez_service, self.adapter_path)
        self.adapter_properties = dbus.Interface(self.adapter_proxy, constants.properties_interface)
        self.adapter = dbus.Interface(self.adapter_proxy, constants.adapter_interface)
        self.object_manager = dbus.Interface(self.bus.get_object(constants.bluez_service, "/"), constants.object_manager_interface)
        self.last_session_path = None
        self.opp_process = None
        self.stream_process = None

    def get_paired_devices(self):
        """Retrieves all Bluetooth devices that are currently paired with the adapter.

        Returns:
            paired_devices: A dictionary of paired devices.
        """
        paired_devices = {}
        for path, interfaces in self.object_manager.GetManagedObjects().items():
            if constants.device_interface in interfaces:
                device = interfaces[constants.device_interface]
                if device.get("Paired") and device.get("Adapter") == self.adapter_path:
                    address = device.get("Address")
                    name = device.get("Name", "Unknown")
                    paired_devices[address] = name
        return paired_devices

    def start_discovery(self):
        """Start scanning for nearby Bluetooth devices, if not already discovering."""
        try:
            if not self.adapter_properties.Get(constants.adapter_interface, "Discovering"):
                self.adapter.StartDiscovery()
                self.log.info("Discovery started.")
            else:
                self.log.info("Discovery already in progress.")
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to start discovery: %s", error)

    def stop_discovery(self):
        """Stop Bluetooth device discovery, if it's running."""
        try:
            if self.adapter_properties.Get(constants.adapter_interface, "Discovering"):
                self.adapter.StopDiscovery()
                self.log.info("Discovery stopped.")
            else:
                self.log.info("Discovery is not running.")
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to stop discovery: %s", error)

    def get_discovered_devices(self):
        """Retrieve discovered Bluetooth devices under the current adapter.

        Returns:
            discovered_devices: List of discovered Bluetooth devices.
        """
        discovered_devices = []
        for path, interfaces in self.object_manager.GetManagedObjects().items():
            device = interfaces.get(constants.device_interface)
            if not device or device.get("Adapter") != self.adapter_path:
                continue
            address = device.get("Address")
            alias = device.get("Alias", "Unknown")
            if address:
                discovered_devices.append({
                    "path": path,
                    "address": address,
                    "alias": alias})
            else:
                self.log.warning("Failed to extract device info from %s", path)
        return discovered_devices

    def find_device_path(self, address):
        """Find the D-Bus object path of a device by address under the correct adapter.

        Args:
            address: Bluetooth address of remote device.

        Returns:
            path: D-Bus object path or None if not found.
        """
        formatted_interface_path = f"{constants.bluez_path}/{self.interface}/"
        for path, interfaces in self.object_manager.GetManagedObjects().items():
            if constants.device_interface in interfaces:
                if formatted_interface_path in path:
                    properties = interfaces[constants.device_interface]
                    if properties.get("Address") == address:
                        return path
                    else:
                        self.log.warning("Device path not found")

    def register_agent(self, capability=None):
        """Register this object as a Bluetooth pairing agent."""
        try:
            agent_manager = dbus.Interface(self.bus.get_object(constants.bluez_service, constants.bluez_path), constants.agent_interface)
            agent_manager.RegisterAgent(constants.agent_path, capability)
            agent_manager.RequestDefaultAgent(constants.agent_path)
            self.log.info("Registered with capability:%s", capability)
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to register agent: %s", error)
            return False

    def pair(self, address):
        """Pairs with a Bluetooth device using the given controller interface.

        Args:
            address: Bluetooth address of remote device.

        Returns:
            True if successfully paired, False otherwise.
        """
        device_path = self.find_device_path(address)
        if not device_path:
            self.log.info("Device path not found for %s on %s", address, self.interface)
            return False
        try:
            device_proxy = self.bus.get_object(constants.bluez_service, device_path)
            device = dbus.Interface(device_proxy, constants.device_interface)
            properties = dbus.Interface(device_proxy, constants.properties_interface)
            paired = properties.Get(constants.device_interface, "Paired")
            if paired:
                self.log.info("Device %s is already paired.", address)
                return True
            self.log.info("Initiating pairing with %s", address)
            device.Pair()
            paired = properties.Get(constants.device_interface, "Paired")
            if paired:
                self.log.info("Successfully paired with %s", address)
                return True
            self.log.warning("Pairing not confirmed with %s within the timeout period.", address)
            return False
        except dbus.exceptions.DBusException as error:
            self.log.error("Pairing failed with %s: %s", address, error)

    def connect(self, address):
        """Establish a  connection to the specified Bluetooth device.

        Args:
            address: Bluetooth device address of remote device.

        Returns:
            True if connected, False otherwise.
        """
        device_path = self.find_device_path(address)
        if device_path:
            try:
                device = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.device_interface)
                device.Connect()
                properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.properties_interface)
                connected = properties.Get(constants.device_interface, "Connected")
                if connected:
                    self.log.info("Connection successful to %s", address)
                    return True
            except Exception as error:
                self.log.info("Connection failed:%s", error)
                return False
        else:
            self.log.info("Device path not found for address %s", address)
            return False

    def disconnect(self, address):
        """Disconnect a Bluetooth  device from the specified adapter.

        Args:
            address: Bluetooth  address of the remote device.

        Returns:
            True if disconnected or already disconnected, False if an error occurred.
        """
        device_path = self.find_device_path(address)
        if device_path:
            try:
                device = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.device_interface)
                properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.properties_interface)
                connected = properties.Get(constants.device_interface, "Connected")
                if not connected:
                    self.log.info("Device %s is already disconnected.", address)
                    return True
                device.Disconnect()
                return True
            except dbus.exceptions.DBusException as error:
                self.log.info("Error disconnecting device %s:%s", address, error)
        else:
            self.log.warning("Device path not found for address: %s", address)
        self.log.info("Disconnection failed for device: %s", address)
        return False

    def unpair_device(self, address):
        """Unpairs a paired or known Bluetooth device from the system using BlueZ D-Bus.

        Args:
            address: The Bluetooth address of the remote device.

        Returns:
            True if the device was unpaired successfully or already not present,
            False if the unpairing failed or the device still exists afterward.
        """
        try:
            target_path = None
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.device_interface in interfaces:
                    if interfaces[constants.device_interface].get("Address") == address and path.startswith(self.adapter_path):
                        target_path = path
                        break
            if not target_path:
                self.log.info("Device with address %s not found on %s", address, self.interface)
                return True
            self.adapter.RemoveDevice(target_path)
            self.log.info("Requested unpair of device %s at path %s", address, target_path)
            time.sleep(0.5)
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.device_interface in interfaces:
                    if interfaces[constants.device_interface].get("Address") == address:
                        self.log.warning("Device %s still exists after attempted unpair", address)
                        return False
            self.log.info("Device %s unpaired successfully", address)
            return True
        except dbus.exceptions.DBusException as error:
            self.log.error("DBusException while unpairing device %s: %s", address, error)
            return False

    def set_discoverable(self, enable):
        """Makes the Bluetooth device discoverable.

        Args:
            enable: True to enable, False to disable.
        """
        self.log.info("Setting Bluetooth device to be discoverable...")
        if enable:
            command = f"hciconfig {self.interface} piscan"
            subprocess.run(command, shell=True)
            self.log.info("Bluetooth device is now discoverable.")
        else:
            self.log.info("Setting Bluetooth device to be non-discoverable...")
            command = f"hciconfig {self.interface} noscan"
            subprocess.run(command, shell=True)
            self.log.info("Bluetooth device is now non-discoverable.")

    def get_device_address_from_path(self, device_path):
        """
        Given a D-Bus device object path, returns the Bluetooth address.

        Args:
            device_path: The D-Bus object path for the device (e.g. /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX)

        Returns:
            Bluetooth address in standard format (e.g., XX:XX:XX:XX:XX:XX)
        """
        try:
            device_proxy = self.bus.get_object("org.bluez", device_path)
            device_props = dbus.Interface(device_proxy, "org.freedesktop.DBus.Properties")
            address = device_props.Get("org.bluez.Device1", "Address")
            return str(address)
        except Exception as e:
            self.log.error(f"Failed to get device address from path {device_path}: {e}")
            return "Unknown"
