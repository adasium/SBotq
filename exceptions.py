class CommandNotFound(Exception):
    def __init__(self, value: str) -> None:
        self.value = value


class DiscordMessageMissingException(Exception):
    pass
