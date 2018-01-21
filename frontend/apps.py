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

        try:
            from .models import Slave
            Slave.objects.all().update(online=False, command_uuid=None)
        except OperationalError:
            pass

        try:
            from .models import Script
            Script.objects.all().update(
                error_code=None,
                is_running=False,
                is_initialized=False,
                current_index=-1,
            )
        except OperationalError:
            pass

        # Flush status tables DO NOT DELETE!
        flush('ProgramStatus')
