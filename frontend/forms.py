"""
This module contains Django `Forms`.
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
    Form for `SlaveModel`.
    """

    class Meta:
        """
        Meta class
        """
        model = SlaveModel
        fields = ['name', 'ip_address', 'mac_address']


class ProgramForm(ModelForm):
    """
    Form for `ProgramModel`.
    """
    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        """
        Meta class
        """
        model = ProgramModel
        fields = ['name', 'path', 'arguments', 'start_time']


class FilesystemForm(ModelForm):
    """
    Form for `FilesystemModel`.
    """
    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        """
        Meta class
        """
        model = FilesystemModel
        fields = [
            'name',
            'source_path',
            'source_type',
            'destination_path',
            'destination_type',
        ]
