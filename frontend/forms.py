"""
This module contains all forms based on the models from the frontend
application.
"""

from django.forms import (
    ModelForm,
    ModelChoiceField,
    HiddenInput,
)

from .models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    Filesystem as FilesystemModel,
)


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


class FilesystemForm(ModelForm):
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
        model = FilesystemModel
        fields = [
            'name',
            'source_path',
            'source_type',
            'destination_path',
            'destination_type',
        ]
