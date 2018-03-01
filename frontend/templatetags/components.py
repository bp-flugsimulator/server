"""
https://docs.djangoproject.com/en/2.0/howto/custom-template-tags/
"""

from django import template

register = template.Library()


@register.inclusion_tag('frontend/slaves/slave.html')
def slave_entry(slave, programs, filesystems):
    """
    Template tag {% slave_entry slave programms %} is used to display a single
    slave.

    Arguments
    ---------
        slave: Slave object
        programs: Array of programs

    Returns
    -------
        A context which maps the slave object to slave and the array of
        programs to programs.
    """
    return {
        'slave': slave,
        'programs': programs,
        'filesystems': filesystems,
    }


@register.inclusion_tag('frontend/slaves/program.html')
def program_entry(program):
    """
    Template tag {% program_entry program %} is used to display a single
    program.

    Arguments
    ---------
        program: Program object

    Returns
    -------
        A context which maps the program object to program.
    """
    return {'program': program}


@register.inclusion_tag('frontend/scripts/script.html')
def script_entry(script):
    """
    Template tag {% script_entry script %} is used to display a single
    script.

    Arguments
    ---------
        script: Script object

    Returns
    -------
        A context which maps the script object to program.
    """
    return {'script': script}


@register.inclusion_tag('frontend/slaves/modal_form.html', takes_context=True)
def modal_form(context, form, prefix):
    """
    Template tag {% modal_form form prefix %} to generate a model which has a
    form inside.

    Arguments
    ---------
        form: A django form.
        prefix: A prefix for the name.

    Returns
    -------
        Returns a context where the django form is mapped to form, the prefix
        string is mapped to prefix and the the csrf_token from the overall
        context is mapped to csrf_token.
    """
    return {
        'form': form,
        'prefix': prefix,
        'csrf_token': context['csrf_token']
    }


@register.inclusion_tag('frontend/slaves/filesystem.html')
def filesystem_entry(filesystem):
    """
    Filesystem tag {% filesystem_entry filesystem %} is used to display a single
    filesystem.

    Arguments
    ---------
        filesystem: filesystem object

    Returns
    -------
        A context which maps the filesystem object to filesystem.
    """
    return {'filesystem': filesystem}


@register.inclusion_tag('frontend/downloads/file.html')
def download_entry(file):
    """
    File tag {% file_entry file %} is used to display a single
    file.

    Arguments
    ---------
        file: File object

    Returns
    -------
        A context which maps the file object to file.
    """
    return {'file': file}


@register.inclusion_tag('frontend/scripts/js_templates.html')
def script_js_templates():
    """
    Returns the javascript templates which are used by the scripts.

    Returns
    -------
        An empty context
    """
    return {}
