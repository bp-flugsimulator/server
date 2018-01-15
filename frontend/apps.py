"""
This module contains the configuration of the 'frontend' application
"""

from django.apps import AppConfig
from django.db.utils import OperationalError


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
        # Flush status tables DO NOT DELETE!
        flush('ProgramStatus', 'SlaveStatus')
