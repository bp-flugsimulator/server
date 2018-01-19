"""
This module contains all forms based on the models from the frontend application.
"""

from django.forms import (
    ModelForm,
    ModelChoiceField,
    HiddenInput,
)

from .models import Slave as SlaveModel
from .models import Program as ProgramModel
from .models import File as FileModel
from .models import Script as ScriptModel


class SlaveForm(ModelForm):
    """
    Form based on the slave model
    """

    class Meta:
        """
        configures the form
        """
        model = SlaveModel
        fields = ['name', 'ip_address', 'mac_address']


class ProgramForm(ModelForm):
    """
    Form based on the program model
    """
    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        """
        configures the form
        """
        model = ProgramModel
        fields = ['name', 'path', 'arguments', 'start_time']


class FileForm(ModelForm):
    """
    Form based on the program model
    """
    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        """
        configures the form
        """
        model = FileModel
        fields = ['name', 'sourcePath', 'destinationPath']
