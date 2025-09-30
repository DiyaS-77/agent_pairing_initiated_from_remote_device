import dbus.service

from libraries.bluetooth import constants


class Agent(dbus.service.Object):
    def __init__(self, bus, path, ui_callback, log):
        super().__init__(bus, path)
        self.ui_callback = ui_callback
        self.log = log

    @dbus.service.method(constants.agent, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        pin = self.ui_callback("pin", device)
        if not pin:
            self.log.info("User cancelled PIN input")
            raise dbus.DBusException("org.bluez.Error.Rejected", "User cancelled PIN input")
        return str(pin)

    @dbus.service.method(constants.agent, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        passkey = self.ui_callback("passkey", device)
        if passkey is None:
            self.log.info("User cancelled passkey input")
            raise dbus.DBusException("org.bluez.Error.Rejected", "User cancelled passkey input")
        return int(passkey)

    @dbus.service.method(constants.agent, in_signature="ou")
    def RequestConfirmation(self, device, passkey):
        result = self.ui_callback("confirm", device, passkey)
        if result is None:
            self.log.info("User rejected confirmation request")
            raise dbus.DBusException("org.bluez.Error.Rejected", "User rejected confirmation request")
        return

    @dbus.service.method(constants.agent, in_signature="os")
    def DisplayPinCode(self, device, pincode):
        self.log.info("DisplayPinCode for device %s: %s", device, pincode)
        self.ui_callback("display_pin", device, pincode)

    @dbus.service.method(constants.agent, in_signature="ouq")
    def DisplayPasskey(self, device, passkey, entered):
        self.log.info("DisplayPasskey for device %s: %06d (entered %d digits)", device, passkey, entered)
        self.ui_callback("display_passkey", device, passkey, entered)

    @dbus.service.method(constants.agent, in_signature="os")
    def AuthorizeService(self, device, uuid):
        allow = self.ui_callback("authorize", device, uuid)
        if allow is None:
            self.log.info("User rejected the connection")
            raise dbus.DBusException("org.bluez.Error.Rejected", "User rejected the connection")
        return

    @dbus.service.method(constants.agent)
    def Cancel(self):
        self.log.info("Pairing or Connection Cancelled by remote device")
