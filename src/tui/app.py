import asyncio
from datetime import timedelta

from bleak import BleakClient
from textual import on
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Digits, Footer, Header, Label

from src.treadmill.controller import TreadmillController
from src.treadmill.secret import TREADMILL_ADDR, USER_HEIGHT


class SpeedDisplay(Digits):
    """A widget to display the treadmill speed."""


class DurationDisplay(Digits):
    """A widget to display the treadmill duration."""


class CaloriesDisplay(Digits):
    """A widget to display the treadmill calories."""


class DistanceDisplay(Digits):
    """A widget to display the treadmill distance."""


class StepsDisplay(Digits):
    """A widget to display the treadmill steps."""


class TreadmillUpdate(Message):
    """Custom message to update UI with treadmill telemetry."""

    def __init__(self, data):
        super().__init__()
        self.data = data


class TreadMillApp(App):
    """A Textual App to manage FTMS enabled treadmill."""

    BINDINGS = []

    def __init__(
        self, treadmill_controller: TreadmillController, telemetry_queue: asyncio.Queue
    ):
        super().__init__()
        self.queue = telemetry_queue
        self.controller = treadmill_controller

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield VerticalScroll(
            HorizontalGroup(
                Button("Stop", id="stop", variant="error"),
                Button("Start", id="start", variant="success"),
            ),
            HorizontalGroup(
                Button("-", id="dec_speed", variant="error"),
                Button("+", id="inc_speed", variant="success"),
            ),
            HorizontalGroup(Label("Duratinon"), DurationDisplay("00:00:00")),
            HorizontalGroup(Label("Speed"), SpeedDisplay("00.0")),
            HorizontalGroup(Label("Calories"), CaloriesDisplay("000")),
            HorizontalGroup(Label("Distance"), DistanceDisplay("0000")),
            HorizontalGroup(Label("Steps"), StepsDisplay("0000")),
        )

    @on(Button.Pressed, "#start")
    async def start_treadmill(self):
        await self.controller.start()

    @on(Button.Pressed, "#stop")
    async def stop_treadmill(self):
        await self.controller.stop()

    @on(Button.Pressed, "#inc_speed")
    async def increase_speed_treadmill(self):
        await self.controller.set_speed(2)

    @on(Button.Pressed, "#dec_speed")
    async def decrease_speed_treadmill(self):
        await self.controller.set_speed(1)

    async def watch_queue(self):
        while True:
            data_raw = await self.queue.get()

            data = {
                "speed": f"{data_raw["speed"]:05.2f}",
                "distance": f"{data_raw["distance"]:04d}",
                "calories": f"{data_raw["calories"]:04d}",
                "duration": str(timedelta(seconds=data_raw["time"])),
                "steps": str(int(int(data_raw["distance"]) / (int(USER_HEIGHT) / 100 * 0.415))),
            }

            self.post_message(TreadmillUpdate(data))

    async def on_mount(self):
        """Start the worker task."""
        self.run_worker(self.watch_queue(), exclusive=True)

    async def on_treadmill_update(self, event: TreadmillUpdate):
        data = event.data
        self.query_one(SpeedDisplay).update(data["speed"])
        self.query_one(DurationDisplay).update(data["duration"])
        self.query_one(DistanceDisplay).update(data["distance"])
        self.query_one(CaloriesDisplay).update(data["calories"])
        self.query_one(StepsDisplay).update(data["steps"])


async def run():
    print("Started Run")
    data_point_uuid = "00002acd-0000-1000-8000-00805f9b34fb"
    control_point_uuid = "00002ad9-0000-1000-8000-00805f9b34fb"
    telemetry_queue = asyncio.Queue(maxsize=5)

    async with BleakClient(TREADMILL_ADDR) as client:
        print("Connected")

        treadmill_controller = TreadmillController(
            client, control_point_uuid, data_point_uuid, telemetry_queue
        )
        task = asyncio.create_task(treadmill_controller.subscribe())

        app = TreadMillApp(treadmill_controller, telemetry_queue)
        await app.run_async()

    task.cancel()
    await task
    # treadmill_controller.stop_event.is_set()
    # await client.stop_notify(data_point_uuid)


if __name__ == "__main__":
    asyncio.run(run())
