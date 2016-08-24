import collections
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape
from iospec import parse_string as parse_iospec
from lazyutils import lazy

from codeschool import models, panels
from codeschool.core.models import ProgrammingLanguage
from codeschool.lms.activities.models.submission import md5hash

from ..models import CodingIoQuestion
from ..models.question import run_code, differ


class AnswerKeyQueryset(models.QuerySet):
    use_for_related_fields = True

    def language(self, language):
        """
        Filter answer keys by language.
        """

        return self.filter(language=language)

    def iospec_list(self):
        """
        Iterates over distinct iospec objects.
        """
        #TODO: implement
        raise NotImplementedError

    def iospec_source_list(self):
        """
        Iterates over distinct iospec sources.
        """
        #TODO: implement
        raise NotImplementedError

    def has_program(self):
        """
        Return true if some source code program is defined for the given
        queryset.
        """

        for src in self.values_list('source', flat=True):
            if src:
                return True
        return False


class AnswerKey(models.Model):
    """
    Represents an answer to some question given in some specific computer
    language plus the placeholder text that should be displayed.
    """

    class ValidationError(Exception):
        pass

    class Meta:
        verbose_name = _('answer key')
        verbose_name_plural = _('answer keys')
        unique_together = [('question', 'language')]

    question = models.ParentalKey(
        CodingIoQuestion,
        related_name='answers'
    )
    language = models.ForeignKey(
        ProgrammingLanguage,
        related_name='+',
    )
    source = models.TextField(
        _('answer source code'),
        blank=True,
        help_text=_(
            'Source code for the correct answer in the given programming '
            'language.'
        ),
    )
    placeholder = models.TextField(
        _('placeholder source code'),
        blank=True,
        help_text=_(
            'This optional field controls which code should be placed in '
            'the source code editor when a question is opened. This is '
            'useful to put boilerplate or even a full program that the '
            'student should modify. It is possible to configure a global '
            'per-language boilerplate and leave this field blank.'
        ),
    )
    source_hash = models.CharField(
        max_length=32,
        blank=True,
        help_text=_('Hash computed from the reference source'),
    )
    iospec_hash = models.CharField(
        max_length=32,
        blank=True,
        help_text=_('Hash computed from reference source and iospec_size.'),
    )
    iospec_source = models.TextField(
        _('expanded source'),
        blank=True,
        help_text=_(
            'Iospec source for the expanded testcase. This data is computed '
            'from the reference iospec source and the given reference program '
            'to expand the outputs from the given inputs.'
        )
    )

    objects = AnswerKeyQueryset.as_manager()
    iospec_size = property(lambda x: x.question.iospec_size)

    @lazy
    def iospec(self):
        return parse_iospec(self.iospec_source)

    def __repr__(self):
        return '<AnswerKeyItem: %s (%s)>' % (self.question, self.language)

    def __str__(self):
        return '%s (%s)>' % (self.question, self.language)

    def clean(self):
        super().clean()

        if self.question is None:
            return

        # We only have to update if the parent's hash is incompatible with the
        # current hash and the source field is defined. We make this test to
        # perform the expensive code re-evaluation only when strictly necessary
        parent_hash = self.parent_hash()
        source_hash = md5hash(self.source)

        if parent_hash != self.iospec_hash or source_hash != self.source_hash:
            try:
                iospec = self.question.iospec
            except Exception:
                raise ValidationError(_(
                    'cannot register answer key for question with invalid '
                    'iospec.'
                ))
            result = self._update_state(iospec, self.source, self.language)
            self.iospec_source = result.source()
            self.source_hash = source_hash
            self.iospec_hash = parent_hash

    def update(self, commit=True):
        """
        Update the internal iospec source and hash keys to match the given
        parent iospec value.

        It raises a ValidationError if the source code is invalid.
        """

        iospec = self.question.iospec
        result = self._update_state(iospec, self.source, self.language)
        self.iospec_source = result.source()
        self.source_hash = md5hash(self.source)
        self.iospec_hash = self.parent_hash()
        if commit:
            self.save()

    def _update_state(self, iospec, source, language):
        """
        Worker function for the .update() and .clean() methods.

        Update the hashes and the expanded iospec_source for the answer key.
        """

        # We expand inputs and compute the result for the given source code
        # string
        language = language.ejudge_ref()
        if len(iospec) <= self.iospec_size:
            iospec.expand_inputs(self.iospec_size)
        result = run_code(source, iospec, language)

        # Check if the result has runtime or build errors
        if result.has_errors:
            for testcase in iospec:
                result = run_code(source, testcase, language)
                if result.has_errors:
                    error_dic = {
                        'error': escape(result.get_error_message()),
                        'iospec': escape(testcase.source())
                    }
                    raise ValidationError({
                        'source': mark_safe(ERROR_TEMPLATE % error_dic)
                    })

        # The source may run fine, but still give results that are inconsistent
        # with the given testcases. This will only be noticed if the user
        # provides at least one simple IO test case.
        for (expected, value) in zip(iospec, result):
            expected_source = expected.source().rstrip()
            value_source = value.source().rstrip()
            if expected.is_simple and expected_source != value_source:
                msg = _(
                    '<div class="error-message">'
                    'Your program produced invalid results in this tescase:\n'
                    '<br>\n'
                    '<pre>%(diff)s</pre>\n'
                    '</div>'
                )
                error = {
                    'diff': '\n'.join(differ.compare(
                        expected.source().rstrip().splitlines(),
                        value.source().rstrip().splitlines()
                    ))
                }
                msg = mark_safe(msg % error)
                raise ValidationError({'source': msg})

        # Now we save the result because it has all the computed expansions
        return result

    def save(self, *args, **kwds):
        if 'iospec' in self.__dict__:
            self.iospec_source = self.iospec.source()
        super().save(*args, **kwds)

    def run(self, source=None, iospec=None):
        """
        Runs the given source against the given iospec.

        If no source is given, use the reference implementation.

        If no iospec is given, user the default. The user may also pass a list
        of input strings.
        """

        source = source or self.source
        iospec = iospec or self.iospec
        if not source:
            raise ValueError('a source code string must be provided.')

        return run_code(source, iospec, self.language.ejudge_ref())

    def parent_hash(self):
        """
        Return the iospec hash from the question current iospec/iospec_size.
        """

        parent = self.question
        return md5hash(parent.iospec_source + str(parent.iospec_size))

    # Wagtail admin
    panels = [
        panels.FieldPanel('language'),
        panels.FieldPanel('source'),
        panels.FieldPanel('placeholder'),
    ]


class RelatedAnswerKeyManager(collections.Mapping, models.RelatedManagerExt):
    """
    A related manager to be used in the 'answers' attribute of CodingIoQuestion
    instances.
    """

    _NOT_GIVEN = object()

    def __getitem__(self, language):
        return self.from_language(language)

    def __iter__(self):
        for lang_id in self.values_list('language', flat=True):
            yield ProgrammingLanguage.objects.get(id=lang_id)

    def __len__(self):
        return self.count()

    def has_program(self):
        """
        Return true if some source code program is defined for the given
        queryset.
        """

        from pprint import pprint as print
        print(self.instance.__dict__)
        print(self.all())
        print(self.get_object_list())
        print(self.get_live_queryset())

        for src in self.values_list('source', flat=True):
            if src:
                return True
        return False

    def get(self, language, default=_NOT_GIVEN):
        if default is self._NOT_GIVEN:
            return super(collections.Mapping, self).get(language=language)
        else:
            return collections.Mapping.get(self, language, default)

    def is_complete(self):
        """
        Return True if an answer key item exists for all valid programming
        languages.
        """

        refs = self.values_list('language__ref', flatten=True)
        all_refs = ProgrammingLanguage.objects.values('ref', flatten=True)
        return set(all_refs) == set(refs)

    def from_language(self, language):
        """
        Return the AnswerKey instance for the requested language or None if
        no object is found.
        """

        try:
            return self.get(language=language)
        except self.model.DoesNotExist:
            return None

    def iospec(self, language, force_expanded=True):
        """
        Return the IoSpec object associated with the given language.

        If ``force_expanded=True``, raises an error if it cannot find an
        expanded iospec object. This happens if there is no answer key defined
        for the question and if the main iospec requires command expansions.
        """

        try:
            return self.get(language=language).iospec
        except self.model.DoesNotExist:
            sources = self.values_list('iospec_source', flat=True).distinct()
            if sources:
                source, *_ = sources
                return parse_iospec(source)
            else:
                iospec = self.instance.iospec
                if force_expanded and not iospec.is_simple:
                    source = self.instance.iospec_source
                    source = ('    ' + line for line in source.splitlines())
                    source = '\n'.join(source)
                    raise TypeError(
                        'Could not expand iospec source:\n %s' % source
                    )
                return iospec

CodingIoQuestion.answers = RelatedAnswerKeyManager(CodingIoQuestion.answers)


#
# Constants
#
ERROR_TEMPLATE = _("""
Errors produced when executing program with code</p>
<pre class="error-message" style="margin-left: 2em">%(iospec)s</pre>

<p class="error-message">Error message:
<pre class="error-message" style="margin-left: 2em">%(error)s</pre>
<p class="hidden">
""")
