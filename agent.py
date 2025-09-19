import dbus
import dbus.mainloop.glib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

AGENT_INTERFACE = 'org.bluez.Agent1'

class Agent(dbus.service.Object):
    def __init__(self, bus, path, ui_callback):
        self.ui_callback = ui_callback

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        return self.ui_callback("pin", device)

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPassKey(self, device):
        return self.ui_callback("passkey", device)

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="ou")
    def AuthorizeService(self, device, uuid):
        return self.ui_callback("authorize", device, uuid)
