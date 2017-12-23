from django import template

register = template.Library()


@register.inclusion_tag('frontend/slaves/slave.html')
def slave_entry(slave, programs):
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
    }


@register.inclusion_tag('frontend/slaves/program.html')
def program_entry(program):
    """
    Template tag {% program_entry program %} is used to display a single
    program.

    Arguments
    ---------
        programs: Program object

    Returns
    -------
        A context which maps the program object to program.
    """
    return {'program': program}


@register.inclusion_tag('frontend/slaves/modal_form.html', takes_context=True)
def modal_form(context, form, prefix):
    """
    Template tag {% modal_form form prefix %} to generate a model wich has a
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
