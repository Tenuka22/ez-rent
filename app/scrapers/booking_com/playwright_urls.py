from enum import Enum
from typing import Dict


class BookingComRoute(Enum):
    HOME = "home"


class BookingComUrls:
    def __init__(self) -> None:
        self._urls: Dict[BookingComRoute, str] = {
            BookingComRoute.HOME: "https://www.booking.com",
        }

    def get(self, route: BookingComRoute) -> str:
        return self._urls[route]

    @property
    def home(self) -> str:
        return self.get(BookingComRoute.HOME)
