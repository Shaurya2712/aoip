# STATUS: COMPLETE


class JobSkipped(Exception):
    """Raised when a job intentionally skips work (e.g. missing optional credentials)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)
