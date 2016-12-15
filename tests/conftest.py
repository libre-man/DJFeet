from libfaketime import reexec_if_needed
import pytest


def pytest_configure():
    reexec_if_needed()


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="run slow tests")
