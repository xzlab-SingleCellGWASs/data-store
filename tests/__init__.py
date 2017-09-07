import datetime
import unittest

import time
from unittest.runner import TextTestResult

class TimeLoggingTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_timings = []

    def startTest(self, test):
        self._test_started_at = time.time()
        super().startTest(test)

    def addSuccess(self, test):
        elapsed = time.time() - self._test_started_at
        name = self.getDescription(test)
        self.test_timings.append((name, elapsed))
        super().addSuccess(test)

    def getTestTimings(self):
        return self.test_timings

class TimeLoggingTestRunner(unittest.TextTestRunner):
    slow_test_threshold = 8.0
    def __init__(self, *args, **kwargs):
        return super().__init__(resultclass=TimeLoggingTestResult, *args, **kwargs)

    def run(self, test):
        result = super().run(test)
        self.stream.writeln("\nSlow Tests (>{:.03}s):".format(self.slow_test_threshold))
        for name, elapsed in result.getTestTimings():
            if elapsed > self.slow_test_threshold:
                self.stream.writeln("({:.03}s) {}".format(elapsed, name))
        return result

class DSSTestProgram(unittest.TestProgram):
    def runTests(self):
        self.testRunner = TimeLoggingTestRunner
        unittest.TestProgram._runTests(self)

unittest.TestProgram._runTests = unittest.TestProgram.runTests
unittest.TestProgram.runTests = DSSTestProgram.runTests

def get_version():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%S.%fZ")
