from django import template
register = template.Library()
@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items(): query[key] = value
    return query.urlencode()
@register.filter
def nice_status(value):
    return str(value).replace('_', ' ').title()
