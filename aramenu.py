import json
import os

import aranet4
import rumps


def scan_for_devices():
    devices = set()

    def add_device(advertisement):
        devices.add((advertisement.device.name, advertisement.device.address))

    aranet4.client.find_nearby(add_device)

    return devices


def choose_device():
    devices = scan_for_devices()

    if not devices:
        window = rumps.Window(
            title="No device found",
            message="No device found. Please ensure the device is turned on and in range. Press OK to try again.",
            ok="OK",
            cancel=True,
            dimensions=(0, 0),
        )
        response = window.run()

        if response.clicked:
            return choose_device()
        else:
            rumps.quit_application()

    if len(devices) == 1:
        window = rumps.Window(
            title="Found a device",
            message=f"Select {list(devices)[0][0]}",
            ok="OK",
            cancel=True,
            dimensions=(0, 0),
        )
        response = window.run()

        if response.clicked:
            return list(devices)[0][1]
        else:
            rumps.quit_application()


def setup_device() -> str:
    window = rumps.Window(
        title="No device found",
        message="Ensure Bluetooth is enabled and press OK to scan for devices. This might take a few seconds.",
        ok="OK",
        cancel=True,
        dimensions=(0, 0),
    )
    response = window.run()

    if not response.clicked:
        rumps.quit_application()

    device = choose_device()

    # Write the configuration to ~/.aramenu/config.json, creating dir and file if necessary
    os.makedirs(os.path.expanduser("~/.aramenu"), exist_ok=True)
    with open(os.path.expanduser("~/.aramenu/config.json"), "w") as f:
        json.dump({"current_device": device}, f)

    return device


def get_status_icon(status: aranet4.client.Status):
    match status.name:
        case "GREEN":
            return "🟢"
        case "AMBER":
            return "🟡"
        case "RED":
            return "🔴"


class AramenuApp(rumps.App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Try to load the configuration from ~/.aramenu/config.json
        # If it doesn't exist, create it with the default values
        try:
            with open(os.path.expanduser("~/.aramenu/config.json")) as f:
                config = json.load(f)
                self.current_device = config["current_device"]
        except FileNotFoundError:
            self.current_device = None
        except KeyError:
            self.current_device = None

        if self.current_device is None:
            self.current_device = setup_device()

        self.update_reading()

    @rumps.timer(5)
    def refresh(self, _):
        if self.ago < (self.interval + 5):
            self.ago += 5
            self.menu["Updated"].title = f"Updated {self.ago} seconds ago"
            return

        self.update_reading()

    def update_reading(self):
        reading = aranet4.client.get_current_readings(self.current_device)
        self.interval = reading.interval
        self.ago = reading.ago
        self.reading = reading
        self.update_menu()
        self.update_title()

    def update_menu(self):
        reading = self.reading
        self.menu.clear()
        self.menu = [
            rumps.MenuItem(
                title=f"{get_status_icon(reading.status)} CO₂: {reading.co2} ppm"
            ),
            rumps.MenuItem(title=f"🌡️ Temperature: {reading.temperature} °C"),
            rumps.MenuItem(title=f"💧 Humidity: {reading.humidity}%"),
            rumps.MenuItem(title=f"🔻 Pressure: {reading.pressure} hPa"),
            None,
            (
                rumps.MenuItem(title=reading.name),
                [
                    rumps.MenuItem(title=f"MAC: {self.current_device}"),
                    rumps.MenuItem(title=f"Version: {reading.version}"),
                    rumps.MenuItem(title=f"Interval: {reading.interval} seconds"),
                    rumps.MenuItem(title=f"Battery: {reading.battery}%"),
                ],
            ),
            rumps.MenuItem(title=f"Updated"),
            None,
            # rumps.MenuItem(title="Quit", callback=rumps.quit_application),
        ]
        self.menu["Updated"].title = f"Updated {self.ago} seconds ago"

    def update_title(self):
        self.title = f"{get_status_icon(self.reading.status)} {self.reading.co2}"


if __name__ == "__main__":
    AramenuApp("Aramenu").run(debug=True)
