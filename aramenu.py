import datetime
import json
import os

import aranet4
import rumps


def scan_for_devices() -> set[tuple[str, str]]:
    devices = set()

    def add_device(advertisement):
        devices.add((advertisement.device.name, advertisement.device.address))

    aranet4.client.find_nearby(add_device)

    return devices


def choose_device() -> str:
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

    # Take the first device. If you have more than one, this is not the app for you (yet).
    device = list(devices)[0]

    window = rumps.Window(
        title="Found a device",
        message=f"{device[0]} ({device[1]}) was found. Press OK to use this device.",
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


def reset(_):
    window = rumps.Window(
        title="Reset settings",
        message=(
            "This will delete the configuration file and quit the app. "
            "Open it again to set up a new device. "
            "Press OK to continue."
        ),
        ok="OK",
        cancel=True,
        dimensions=(0, 0),
    )
    response = window.run()

    if response.clicked:
        os.remove(os.path.expanduser("~/.aramenu/config.json"))
        rumps.quit_application()


def get_status_icon(status: aranet4.client.Status) -> str:
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

        # Start the refresh timer, get the interval from the reading
        refresh_interval = getattr(self.reading, "interval", 60)
        self.refresh = rumps.timer(refresh_interval)(self.refresh)

    def refresh(self, _):
        try:
            self.update_reading()
        except Exception as e:
            self.error = e
            self.set_error_state()
            return
        self.error = None

    def update_reading(self):
        self.reading = aranet4.client.get_current_readings(self.current_device)
        self.update_menu()
        self.update_title()

    def update_menu(self):
        reading = self.reading
        reading_time = datetime.datetime.now()
        next_reading_time = reading_time + datetime.timedelta(seconds=reading.interval)

        self.menu.clear()
        self.menu = [
            rumps.MenuItem(title=f"{get_status_icon(reading.status)} CO₂: {reading.co2} ppm"),
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
                    None,
                    rumps.MenuItem(title="Reset settings...", callback=reset),
                ],
            ),
            rumps.MenuItem(title=f"Last reading: {reading_time.strftime('%H:%M:%S')}"),
            rumps.MenuItem(title=f"Next reading: {next_reading_time.strftime('%H:%M:%S')}"),
            None,
            rumps.MenuItem(title="Quit", callback=rumps.quit_application),
        ]

    def update_title(self):
        self.title = f"{get_status_icon(self.reading.status)} {self.reading.co2}"

    def view_error(self, _):
        window = rumps.Window(
            title="Error",
            message="The last reading failed with the following error.",
            ok="OK",
            default_text=str(self.error),
        )
        window.run()

    def set_error_state(self):
        self.title = "⚠️"
        self.menu.clear()
        self.menu = [
            rumps.MenuItem(title="Reading failed"),
            rumps.MenuItem(title="View error...", callback=self.view_error),
            rumps.MenuItem(title="Refresh", callback=self.refresh),
            None,
            rumps.MenuItem(title="Quit", callback=rumps.quit_application),
        ]


if __name__ == "__main__":
    AramenuApp("Aramenu").run(debug=False)
