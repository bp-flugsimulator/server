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
        help_texts = {
            'name':
            r"""Name of the Client, has to be unique
            <hr>
            <code>Simulation Server<code/>""",
            'ip_address':
            r"""IP-Address used by the Client, has to be unique
            <hr>
            <code>123.456.789.101<code/>""",
            'mac_address':
            r"""MAC-Address of the Client, has to be unique
            <hr>
            <code>01:c2:b3:a4:05:06<code/>"""
        }


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
        help_texts = {
            'name':
            r"""Name of the program, has to be unique on one client
            <hr>
            <code>Start Command Line<code/>"""                                                                    ,
            'path':
            r"""Path to the program or other executable.
            <hr>
            <code>C:\Windows\System32\cmd.exe<code/>"""                                                                                                       ,
            'arguments':
            r"""Runs this program with the specified arguments
            <hr>
            <code>/Q<code/> (Turn echo off)"""                                                                                      ,
            'start_time':
            r"""Time the program needs to start
            <hr>
            <code>2<code/>"""
        }


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
        help_texts = {
            'name':
            r"""Name of the filesystem, has to be unique on one client.
            <hr>
            <code>Move Desktop File<code/>""",
            'source_path':
            r"""Path to the file or directory.
            <hr>
            <code>C:\Users\Username\Desktop\settings_me.txt<code/>""",
            'source_type':
            r"""<b>File:</b> Source is a file (should end with a filename extension) <br>
            <b>Directory:</b> Source is a directory and its contents will be moved.
            <hr>
            <code>File<code/>""",
            'destination_path':
            r"""Path to the file or directory the source will be moved to.
            <hr>
            <code>C:\Users\Username\Desktop\Config\settings.txt<code/>""",
            'destination_type':
            r"""<b>Replace with:</b> Source will be moved and renamed to destination <br>
            <b>Insert into:</b> Destination has to be a folder and source
            will be placed inside the destination.
            <hr>
            <code>Replace with<code/>"""
        }
