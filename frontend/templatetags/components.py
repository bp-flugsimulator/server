from django import template

register = template.Library()


@register.inclusion_tag('frontend/slaves/slave.html')
def slave_entry(slave, programs):
    return {
        'slave': slave,
        'programs': programs,
    }


@register.inclusion_tag('frontend/slaves/program.html')
def program_entry(program):
    return {'program': program}


@register.inclusion_tag('frontend/slaves/modal_form.html', takes_context=True)
def modal_form(context, form, prefix):
    return {
        'form': form,
        'prefix': prefix,
        'csrf_token': context['csrf_token']
    }
