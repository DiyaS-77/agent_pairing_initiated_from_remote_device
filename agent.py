import dbus
import dbus.service
import dbus.mainloop.glib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

AGENT_INTERFACE = 'org.bluez.Agent1'

class Agent(dbus.service.Object):
    def __init__(self, bus, path, pairing_callback=None):
        super().__init__(bus, path)
        self.pairing_callback = pairing_callback

    def _handle_pairing_request(self, device_path):
        if self.on_request_pairing:
            # Ensure this runs on the Qt GUI thread
            self.on_request_pairing(device_path)

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device_path):
        print(f"[Agent] RequestAuthorization: {device_path}")
        self._handle_pairing_request(device_path)

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device_path):
        print(f"[Agent] RequestPinCode: {device_path}")
        self._handle_pairing_request(device_path)
        return "0000"  # or use user input later

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device_path):
        print(f"[Agent] RequestPasskey: {device_path}")
        self._handle_pairing_request(device_path)
        return dbus.UInt32(123456)  # you can randomize or ask user

    @dbus.service.method(AGENT_INTERFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device_path, passkey, entered):
        print(f"[Agent] DisplayPasskey: {device_path}, Passkey: {passkey}, Entered: {entered}")
        self._handle_pairing_request(device_path)

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device_path, pincode):
        print(f"[Agent] DisplayPinCode: {device_path}, PIN: {pincode}")
        self._handle_pairing_request(device_path)

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def Cancel(self, device_path):
        print(f"[Agent] Pairing canceled: {device_path}")
