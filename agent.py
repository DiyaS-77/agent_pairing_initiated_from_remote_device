import dbus.service

from libraries.bluetooth import constants


class Agent(dbus.service.Object):
    def __init__(self, bus, path, ui_callback, log, capability):
        super().__init__(bus, path)
        self.ui_callback = ui_callback
        self.log = log
        self.capability= capability

    @dbus.service.method(constants.agent, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        pin = self.ui_callback("pin", device)
        if not pin:
            raise dbus.DBusException("org.bluez.Error.Rejected", "User cancelled PIN input")
        return str(pin)

    @dbus.service.method(constants.agent, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        passkey = self.ui_callback("passkey", device)
        if passkey is None:
            raise dbus.DBusException("org.bluez.Error.Rejected", "User cancelled passkey input")
        return int(passkey)

    @dbus.service.method(constants.agent, in_signature="ou")
    def RequestConfirmation(self, device, passkey):
        result = self.ui_callback("confirm", device, passkey)
        if result is None:
            raise dbus.DBusException("org.bluez.Error.Rejected", "User rejected confirmation request")
        return

    @dbus.service.method(constants.agent, in_signature="os")
    def AuthorizeService(self, device, uuid):
        allow = self.ui_callback("authorize", device, uuid)
        if allow is None:
            raise dbus.DBusException("org.bluez.Error.Rejected", "User rejected the connection")
        return

    @dbus.service.method(constants.agent)
    def Cancel(self):
        self.log.info("Pairing or Connection Cancelled by remote device")
