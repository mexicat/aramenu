import rumps
import aranet4

device_mac = "XXXX"


class AramenuApp(rumps.App):
    def get_icon(self, status: aranet4.client.Status):
        return f"icons/{self.reading.status.name.lower()}.svg"

    @rumps.timer(5)
    def refresh(self, _):
        if self.ago < (self.interval + 5):
            self.ago += 5
            self.update_menu()
            return

        self.update_reading()

    def scan(self, _):
        window = rumps.Window(
            message="Select a device",
            title="Scan",
            default_text="",
            cancel=True,
            dimensions=(300, 200),
        )

        def add_device(advertisement):
            window.add_button(advertisement.device.address)

        aranet4.client.find_nearby(add_device)
        window.run()

    def select_device(self, _):
        print("select_device")

    def update_reading(self):
        reading = aranet4.client.get_current_readings(device_mac)
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
                title=f"CO₂: {reading.co2} ppm",
                icon=self.get_icon(reading.status),
                dimensions=(12, 12),
            ),
            rumps.MenuItem(title=f"Temperature: {reading.temperature} °C"),
            rumps.MenuItem(title=f"Humidity: {reading.humidity}%"),
            rumps.MenuItem(title=f"Pressure: {reading.pressure} hPa"),
            None,
            (
                rumps.MenuItem(title=reading.name),
                [
                    rumps.MenuItem(title=f"MAC: {device_mac}"),
                    rumps.MenuItem(title=f"Version: {reading.version}"),
                    rumps.MenuItem(title=f"Interval: {reading.interval} seconds"),
                    rumps.MenuItem(title=f"Battery: {reading.battery}%"),
                    None,
                    rumps.MenuItem(title=f"Scan...", callback=self.scan),
                ],
            ),
            rumps.MenuItem(title=f"Updated {self.ago} seconds ago"),
            None,
            rumps.MenuItem(title="Quit", callback=rumps.quit_application),
        ]

    def update_title(self):
        self.title = f" {self.reading.co2}"
        self.icon = self.get_icon(self.reading.status)


if __name__ == "__main__":
    current = aranet4.client.get_current_readings(device_mac)
    print(current)
    app = AramenuApp("Loading...")
    app.update_reading()
    app.run()
