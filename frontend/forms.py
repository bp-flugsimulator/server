"""
This module contains Django `Forms`.
"""

from django.forms import (
    ModelForm,
    ModelChoiceField,
    HiddenInput,
    Textarea
)

from .models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    Filesystem as FilesystemModel,
)

class BaseModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super(BaseModelForm, self).__init__(*args, **kwargs)

class SlaveForm(BaseModelForm):
    """
    Form for `SlaveModel`.
    """

    class Meta:
        """
        Meta class
        """
        labels = {'name': 'Display Name'}
        model = SlaveModel
        fields = ['name', 'ip_address', 'mac_address']
        help_texts = {
            'name':
            r"""<b>Description</b><br>
            Name of the client, has to be unique
            <hr>
            <b>Example</b><br>
            <code>Simulation Server</code>""",
            'ip_address':
            r"""<b>Description</b><br>
            IP-Address used by the client, has to be unique
            <hr>
            <b>Example</b><br>
            <code>123.456.789.101</code>""",
            'mac_address':
            r"""<b>Description</b><br>
            MAC-Address of the client, has to be unique
            <hr>
            <b>Example</b><br>
            <code>01:c2:b3:a4:05:06</code>"""
        }


class ProgramForm(BaseModelForm):
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
        labels = {'name': 'Display Name', 'path': 'Path to executable'}
        model = ProgramModel
        fields = ['name', 'path', 'arguments', 'start_time']
        widgets = {'path': Textarea(attrs={'rows':1}),
                'arguments': Textarea(attrs={'rows':1}),}
        help_texts = {
            'name':
            r"""<b>Description</b><br>
            Name of the program, has to be unique on one client.
            <hr>
            <b>Example</b><br>
            <code>Start Command Line</code>""",
            'path':
            r"""<b>Description</b><br>
            Path to the program or other executable.
            <hr>
            <b>Example</b><br>
            <i>Windows</i>: <code>C:\Windows\System32\cmd.exe</code><br>
            <i>Unix</i>: <code>/home/user/apps/terminal</code>""",
            'arguments':
            r"""<b>Description</b><br>
            Runs this program with the specified arguments.
            <hr>
            <b>Example</b><br>
            <i>Windows</i>: <code>/Q</code> (Turn echo off)<br>
            <i>Unix</i>: <code>-c echo</code> (Runs command on terminal)""",
            'start_time':
            r"""<b>Description</b><br>
            This amount specifies the behavior for the program in a script
            execution.<br>
            <code>time >  0</code> Wait for specified seconds<br>
            <code>time == 0</code> Program is finished immediately<br>
            <code>time <  0</code> Wait for the program to stop<br>
            <hr>
            <b>Example</b><br>
            <code>2</code>"""
        }


class FilesystemForm(BaseModelForm):
    """
    Form for `FilesystemModel`.
    """
    labels = {'name': 'Display Name'}
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
        widgets = {'source_path': Textarea(attrs={'rows':1}),
                'destination_path': Textarea(attrs={'rows':1}),}
        help_texts = {
            'name':
            r"""<b>Description</b><br>
            Name of the filesystem, has to be unique on one client.
            <hr>
            <b>Example</b><br>
            <code>Move Desktop File</code>""",
            'source_path':
            r"""<b>Description</b><br>
            Path to a file or directory on the client.
            <hr>
            <b>Example</b><br>
            <i>Windows</i>: <code>C:\Users\Username\Desktop\settings_me.txt</code><br>
            <i>Unix</i>: <code>/home/user/README.txt</code><br>""",
            'source_type':
            r"""<b>Description</b><br>
            <ins>File:</ins> Source path is a file. <br>
            <ins>Directory:</ins> Source path is a directory and the whole
            folder will be moved.
            <hr>
            <b>Example</b><br>
            <code>File</code>""",
            'destination_path':
            r"""<b>Description</b><br>
            A path on the client where the file or directory (specified by
            source path) will be moved to.
            <hr>
            <b>Example</b><br>
            <i>Windows</i>: <code>C:\Users\Username\Desktop\MOVED_settings_me.txt</code><br>
            <i>Unix</i>: <code>/home/user/MOVED_README.txt</code><br>""",
            'destination_type':
            r"""<b>Description</b><br>
            <ins>Rename:</ins> Source path will be moved and renamed to
            destination. <br>
            <ins>Keep Name:</ins> Destination path has to be a folder and
            the file or directory will be placed inside the destination
            directory.
            <hr>
            <b>Example</b><br>
            <code>Replace with</code>"""
        }
