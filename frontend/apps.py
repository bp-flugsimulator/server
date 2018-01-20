"""
This module contains the configuration of the 'frontend' application
"""
import builtins

from django.apps import AppConfig
from django.db.utils import OperationalError
from .scheduler import Scheduler


def flush(*tables):
    """
    Deletes all entries in the given tables.

    Arguments
    ---------
        tables: List of table names (as string)

    """
    from frontend import models

    for table in tables:
        try:
            getattr(models, table).objects.all().delete()
        except AttributeError:
            pass
        except OperationalError:
            pass


class FrontendConfig(AppConfig):
    """
    configures the frontend applications
    """
    name = 'frontend'

    def ready(self):
        # add FSIM_CURRENT_SCHEDULER to the builtins which make it
        # avialabel in every module
        builtins.FSIM_CURRENT_SCHEDULER = Scheduler()

        # Flush status tables DO NOT DELETE!
        flush('ProgramStatus', 'SlaveStatus')

        # removes the status flags from the script
        from .models import Script as ScriptModel
        for script in ScriptModel.objects.all():
            script.reset()
