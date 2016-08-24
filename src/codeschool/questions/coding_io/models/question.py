from collections import OrderedDict
from difflib import Differ

import ejudge
import markio
import srvice
from annoying.functions import get_config
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from iospec import parse_string as parse_iospec
from lazyutils import lazy

from codeschool import models
from codeschool import panels
from codeschool.core.models import ProgrammingLanguage, programming_language
from codeschool.fixes.parent_refresh import register_parent_prefetch
from codeschool.lms.activities.models.submission import md5hash
from codeschool.questions.models import Question

differ = Differ()


# noinspection PyPropertyAccess,PyArgumentList
@register_parent_prefetch
class CodingIoQuestion(Question):
    """
    CodeIo questions evaluate source code and judge them by checking if the
    inputs and corresponding outputs match an expected pattern.
    """

    class Meta:
        verbose_name = _('Programming question (IO-based)')
        verbose_name_plural = _('Programming questions (IO-based)')

    EXT_TO_METHOD_CONVERSIONS = dict(
        Question.EXT_TO_METHOD_CONVERSIONS,
        md='markio',
    )

    iospec_size = models.PositiveIntegerField(
        _('number of iospec template expansions'),
        default=10,
        help_text=_(
            'The desired number of test cases that will be computed after '
            'comparing the iospec template with the answer key. This is only a '
            'suggested value and will only be applied if the response template '
            'uses input commands to generate random input.'),
    )
    iospec_source = models.TextField(
        _('response template'),
        help_text=_(
            'Template used to grade I/O responses. See '
            'http://pythonhosted.org/iospec for a complete reference on the '
            'template format.'),
    )
    iospec_hash = models.CharField(
        max_length=32,
        blank=True,
        help_text=_('A hash to keep track of iospec updates.'),
    )
    timeout = models.FloatField(
        _('timeout in seconds'),
        blank=True,
        default=1.0,
        help_text=_(
            'Defines the maximum runtime the grader will spend evaluating '
            'each test case.'
        ),
    )
    language = models.ForeignKey(
        ProgrammingLanguage,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=_(
            'Programming language associated with question. Leave it blank in '
            'order to accept submissions in any programming language. This '
            'option should be set only for questions that tests specific '
            'programming languages constructs or require techniques that only '
            'make sense in specific programming languages.'
        ),
    )

    __iospec_updated = False
    __answers = ()

    @lazy
    def iospec(self):
        """
        The IoSpec structure corresponding to the iospec_source.
        """

        return parse_iospec(self.iospec_source)

    def __init__(self, *args, **kwargs):
        # Supports automatic conversion between iospec data and iospec_source
        iospec = kwargs.pop('iospec', None)
        if iospec:
            kwargs['iospec_source'] = iospec.source()
            self.iospec = iospec
        super().__init__(*args, **kwargs)

    def load_from_file_data(self, file_data):
        fake_post = super().load_from_file_data(file_data)
        fake_post['iospec_source'] = self.iospec_source
        return fake_post

    def clean(self):
        """
        Validate the iospec_source field.
        """

        super().clean()

        # We first should check if the iospec_source has been changed and would
        # require a possibly expensive validation.
        source = self.iospec_source
        iospec_hash = md5hash(source)
        if self.iospec_hash != iospec_hash:
            try:
                self.iospec = iospec = parse_iospec(self.iospec_source)
            except Exception as ex:
                raise ValidationError(
                    {'iospec_source': _('invalid iospec syntax: %s' % ex)}
                )

            # Now we check if the new iospec requires an answer key code and
            # if it has some answer key defined
            self.__iospec_updated = True
            return
            if (not iospec.is_expanded) and not self.answers.has_program():
                raise ValidationError({'iospec_source': _(
                    'You iospec definition uses a command or an @input block '
                    'and thus requires an example grading code. Please define '
                    'an "Answer Key" item with source code for at least one '
                    'programming language.'
                )})

    def load_from_markio(self, file_data):
        """
        Load question parameters from Markio file.
        """

        data = markio.parse(file_data)

        # Load simple data from markio
        self.title = data.title or self.title
        self.short_description = (data.short_description or
                                  self.short_description)
        self.timeout = data.timeout or self.timeout
        self.author_name = data.author or self.author_name
        self.iospec_source = data.tests or self.iospec_source

        # Load main description
        # noinspection PyUnresolvedReferences
        self.body = markdown_to_blocks(data.description)

        # Add answer keys
        answer_keys = OrderedDict()
        for (lang, answer_key) in data.answer_key.items():
            language = programming_language(lang)
            key = self.answers.create(question=self,
                                      language=language,
                                      source=answer_key)
            answer_keys[lang] = key
        for (lang, placeholder) in data.placeholder.items():
            if placeholder is None:
                continue
            try:
                answer_keys[lang].placeholder = placeholder
            except KeyError:
                language = ProgrammingLanguage.objects.get(lang)
                self.answer_keys.create(question=self,
                                        language=language,
                                        placeholder=placeholder)
        self.__answers = list(answer_keys.values())

    # Serialization methods: support markio and sets it as the default
    # serialization method for CodingIoQuestion's
    @classmethod
    def load_markio(cls, source):
        """
        Creates a CodingIoQuestion object from a Markio object or source
        string and saves the resulting question in the database.

        This function can run without touching the database if the markio file
        does not define any information that should be saved in an answer key.

        Args:
            source:
                A string with the Markio source code.

        Returns:
            question:
                A question object.
        """

        raise NotImplementedError

    def dump_markio(self):
        """
        Serializes question into a string of Markio source.
        """

        tree = markio.Markio(
            title=self.name,
            author=self.author_name,
            timeout=self.timeout,
            short_description=self.short_description,
            description=self.long_description,
            tests=self.iospec_source,
        )

        for key in self.answer_keys.all():
            tree.add_answer_key(key.source, key.language.ref)
            tree.add_placeholder(key.placeholder, key.language.ref)

        return tree.source()

    def full_clean(self, *args, **kwargs):
        if self.__answers:
            self.answers = self.__answers
        super().full_clean(*args, **kwargs)

    def placeholder(self, language=None):
        """
        Return the placeholder text for the given language.
        """

        key = self.answers[language or self.language]
        if key is None:
            return ''
        return key.placeholder

    def reference_source(self, language=None):
        """
        Return the reference source code for the given language or None, if no
        reference is found.
        """

        key = self.answers[language or self.language]
        if key is None:
            return ''
        return key.source

    def run_code(self, source, language=None, iospec=None):
        """
        Run the given source code string of the given programming language
        using the default or the given IoSpec.

        If no code string is given, runs the reference source code, if it
        exists.
        """

        key = self.answers[language or self.language]
        return key.run(source, iospec)

    def update_iospec_source(self):
        """
        Updates the iospec_source attribute with the current iospec object.

        Any modifications made to `self.iospec` must be saved explicitly to
        persist in the database.
        """

        if 'iospec' in self.__dict__:
            self.iospec_source = self.iospec.source()

    def submit(self, user, source=None, language=None, **kwargs):
        # Fetch info from response_data
        response_data = kwargs.get('response_data', {})
        if source is None and 'source' in response_data:
            source = response_data.pop('source')
        if language is None and 'language' in response_data:
            language = response_data.pop('language')

        # Assure language is valid
        language = language or self.language
        if not language:
            raise ValueError('could not determine the programming language for '
                             'the submission')

        # Assure response data is empty
        if response_data:
            key = next(iter(response_data))
            raise TypeError('invalid or duplicate parameter passed to '
                            'response_data: %r' % key)

        # Construct response data and pass it to super
        response_data = {
            'language': language.ref,
            'source': source,
        }

        return super().submit(user, response_data=response_data, **kwargs)

    # Serving pages and routing
    template = 'questions/coding_io/detail.jinja2'
    template_submissions = 'questions/coding_io/submissions.jinja2'

    def get_context(self, request, *args, **kwargs):
        context = dict(super().get_context(request, *args, **kwargs),
                       form=True)

        # Select default mode for the ace editor
        if self.language:
            context['default_mode'] = self.language.ace_mode()
        else:
            context['default_mode'] = get_config('CODESCHOOL_DEFAULT_ACE_MODE',
                                                 'python')

        # Enable language selection
        if self.language is None:
            context['select_language'] = True
            context['languages'] = ProgrammingLanguage.supported.all()
        else:
            context['select_language'] = False

        return context

    @srvice.route(r'^submit-response/$')
    def route_submit(self, client, source=None, language=None, **kwargs):
        """
        Handles student responses via AJAX and a srvice program.
        """

        # User must choose language
        if not language:
            if self.language is None:
                client.dialog('<p class="dialog-text">%s</p>' % _(
                    'Please select the correct language'
                ))
                return
            language = self.language
        else:
            language = programming_language(language)

        # Bug with <ace-editor>?
        if not source or source == '\x01\x01':
            client.dialog('<p class="dialog-text">%s</p>' % _(
                'Internal error: please send it again!'
            ))
            return

        super().route_submit(
            client=client,
            language=language,
            source=source,
        )

    @srvice.route(r'^placeholder/$')
    def route_placeholder(self, request, language):
        """
        Return the placeholder code for some language.
        """

        return self.get_placehoder(language)

    # Wagtail admin
    content_panels = Question.content_panels[:]
    content_panels.insert(-1, panels.MultiFieldPanel([
        panels.FieldPanel('iospec_size'),
        panels.FieldPanel('iospec_source'),
    ], heading=_('IoSpec definitions')))
    content_panels.insert(
        -1,
        panels.InlinePanel('answers', label=_('Answer keys'))
    )
    settings_panels = Question.settings_panels + [
        panels.MultiFieldPanel([
            panels.FieldPanel('language'),
            panels.FieldPanel('timeout'),
        ], heading=_('Options'))
    ]


#
# Utility functions
#
def run_code(source, inputs, lang=None):
    """
    Runs source code with given inputs and return the corresponding IoSpec
    tree.
    """

    return ejudge.run(
        source, inputs, lang,
        raises=False,
        sandbox=get_config('CODESCHOOL_USE_SANDBOX', True)
    )


def grade_code(source, answer_key, lang=None):
    """
    Compare results of running the given source code with the iospec answer
    key.
    """

    return ejudge.grade(
        source, answer_key, lang,
        raises=False,
        sandbox=get_config('CODESCHOOL_USE_SANDBOX', True)
    )


def response_key(data, strip_blank=True, strip_whitespace=True,
                 single_whitespace=True):
    """
    Normalize CodingIoResponseItem response_data to a string.

    Trivial code transformations should be normalized to the same string.
    Currently, we only handle the trivial case of whitespace normalization.

    Args:
        data;
            The response_data dictionary
        strip_blank:
            If True, remove blank lines.
        strip_whitespace:
            If True, strip whitespace before and after each line.
        single_whitespace:
            If True, separate each word by a single whitespace, even if the
            original uses several whitespaces.
    """

    source = data['source']
    lang = data['language']
    lines = source.splitlines()
    if strip_whitespace:
        lines = [line.strip() for line in lines]
    if strip_blank:
        lines = [line for line in lines if line and not line.isspace()]
    if single_whitespace:
        lines = [' '.join(line.split()) for line in lines]
    return '%s\n%s' % (lang, '\n'.join(lines))


def markdown_to_blocks(source):
    """
    Convert a markdown source string to a sequence of blocks.
    """

    block_list = []

    # Maybe we'll need a more sophisticated approach that mixes block types
    # and uses headings, markdown blocks and extended markdown syntax. Let us
    # try the simple dumb approach first.
    # html_source = markdown(source)
    # block_list.append(('paragraph', blocks.RichText(html_source)))
    block_list.append(('markdown', source))
    print(block_list)
    return block_list
