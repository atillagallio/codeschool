from djinga.template import DjingaTemplate, ctxt_to_dict, engines


def render(self, context=None, request=None):
    context = ctxt_to_dict(context) if context else {}

    engine = engines['djinga'].engine
    if engine.debug:
        # send django signal on template rendering if in debug mode
        from django.test import signals
        from django.template.base import Origin
        self.origin = Origin(self.filename)
        signals.template_rendered.send(sender=self,
                                       template=self,
                                       context=context)

    # adds the context processors (without the builtin ones)
    if request is not None:
        for cp in engine.template_context_processors:
            context.update(cp(request))

    res = super(DjingaTemplate, self).render(context)
    return res

DjingaTemplate._render = DjingaTemplate.render
DjingaTemplate.render = render
