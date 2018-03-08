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
        help_texts = {
            'name': 'Name of the Client, has to be unique',
            'ip_address': 'IP-Address used by the Client, has to be unique',
            'mac_address': 'MAC-Address of the Client, has to be unique'
        }


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
        help_texts = {
            'name': 'Name of the program, has to be unique on one client',
            'path': 'Path to the program or other executable',
            'arguments': 'Runs this program with the specified arguments',
            'start_time': 'Time the program needs to start'
        }


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
        help_texts = {
            'name':
            'Name of the filesystem, has to be unique on one client.',
            'source_path':
            'Path to the file or directory.',
            'source_type':
            "<b>File:</b> Source is a file (should end with a filename extension) <br>\
            <b>Directory:</b> Source is a directory and its contents will be moved.",
            'destination_path':
            'Path to the file or directory the source will be moved to.',
            'destination_type':
            "<b>Replace with:</b> Source will be moved and renamed to destination <br>\
            <b>Insert into:</b> Destination has to be a folder and source \
            will be placed inside the destination."
        }
