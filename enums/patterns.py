from enum import Enum

class Patterns(Enum):
    TOP = "top"
    BOTTOM = "bottom"

    @property
    def description(self):
        descriptions = {
            Patterns.TOP: "顶分型",
            Patterns.BOTTOM: "底分型"
        }
        return descriptions[self]