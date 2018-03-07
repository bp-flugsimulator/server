"""
This module contains the configuration of the `frontend` application
"""
import builtins

from django.apps import AppConfig
from django.db.utils import OperationalError
from .scheduler import Scheduler


def flush(*tables):
    """
    Delete all rows in the given `tables`.

    Parameters
    ---------
        tables: list
            Contains the name of all tables which should be flushed.

    """
    from frontend import models

    for table in tables:
        try:
            getattr(models, table).objects.all().delete()
        except OperationalError:
            pass


def reset(*tables):
    """
    Resets all fields for every row in the database for all given `tables`.

    Parameters
    ---------
        tables: list
            Contains the name of all tables which should be reseted.

    """
    from frontend import models

    for table in tables:
        try:
            attr = getattr(models, table)
        except AttributeError:
            raise AttributeError("The table {} does not exist.".format(table))
        try:
            objs = getattr(models, table).objects
        except AttributeError:
            raise AttributeError(
                "The table {} is not a Django.Model".format(table))
        try:
            for obj in objs.all():
                obj.reset()
        except AttributeError:
            raise AttributeError(
                "The table {} has no function `reset(self)`.".format(table))
        except OperationalError:
            pass


class FrontendConfig(AppConfig):
    """
    This class configures the `frontend` application.
    """
    name = 'frontend'

    def ready(self):
        # add FSIM_CURRENT_SCHEDULER to the builtins which make it
        # avialabel in every module
        builtins.FSIM_CURRENT_SCHEDULER = Scheduler()

        # Resets the tables. DO NOT DELETE!
        reset("Slave", "Script", "Filesystem")

        # Flush status tables DO NOT DELETE!
        flush('ProgramStatus')
