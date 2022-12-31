"""

    PyCS Custom Errors to raise for different issues in the code.

"""


class IsNotRAMSESError(Exception):
    """Exception raised when an input is not a RAMSES simulation.

    Attributes:

    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SnapshotError(Exception):
    """Exception raised when an input is not a RAMSES simulation.

    Attributes:

    """

    def __init__(self, message, snapshot=None):
        if not snapshot:
            self.message = message
        else:
            try:
                self.message = message + "--> %s" % snapshot.loadable_keys()
            except Exception:
                self.message = "Snapshot is not a SimSnap..."
        super().__init__(self.message)


class PynbodyPlottingError(Exception):
    """Exception raised when an input is not a RAMSES simulation.

    Attributes:

    """

    def __init__(self, message, snapshot=None):
        self.message = message
        super().__init__(self.message)


class SimulationBackendError(Exception):
    """Exception raised when an input is not a RAMSES simulation.

    Attributes:

    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


if __name__ == '__main__':
    raise IsNotRAMSESError("Somethings")
