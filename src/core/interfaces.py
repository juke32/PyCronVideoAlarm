from abc import ABC, abstractmethod

class PowerManager(ABC):
    @abstractmethod
    def inhibit_sleep(self, reason: str = "Video Alarm Active") -> bool:
        """Prevent the system from sleeping."""
        pass

    @abstractmethod
    def uninhibit_sleep(self) -> bool:
        """Allow the system to sleep again."""
        pass

class DisplayManager(ABC):
    @abstractmethod
    def turn_off(self) -> bool:
        """Turn off the display to save power or prepare for alarm."""
        pass

    @abstractmethod
    def turn_on(self) -> bool:
        """Turn on the display."""
        pass

    @abstractmethod
    def set_brightness(self, level: int) -> bool:
        """Set display brightness (0-100)."""
        pass

    @abstractmethod
    def get_brightness(self) -> int:
        """Get current brightness level."""
        pass
