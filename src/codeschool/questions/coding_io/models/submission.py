import iospec.feedback
from lazyutils import lazy

from codeschool.core.models import ProgrammingLanguage, programming_language
from codeschool.lms.activities.models import register_submission_class
from codeschool.render import render_html
from ...models import QuestionSubmission
from ..models import CodingIoQuestion
from ..models.question import grade_code


@register_submission_class(CodingIoQuestion)
class CodingIoSubmission(QuestionSubmission):
    """
    A response proxy class specialized in CodingIoQuestion responses.
    """

    class Meta:
        proxy = True

    @property
    def source(self):
        return self.response_data.get('source', '')

    @source.setter
    def source(self, value):
        self.response_data['source'] = value

    @property
    def language(self):
        try:
            lang_id = self.response_data['language']
            return ProgrammingLanguage.get_language(ref=lang_id)
        except (KeyError, ProgrammingLanguage.DoesNotExist):
            return None

    @language.setter
    def language(self, value):
        self.response_data['language'] = programming_language(value).ref

    @lazy
    def feedback(self):
        if not self.feedback_data:
            return None

        data = dict(self.feedback_data)
        data['grade'] = self.final_grade / 100
        del data['source']
        del data['language']
        return iospec.feedback.Feedback.from_json(data)

    feedback_title = property(lambda x: x.feedback and x.feedback.title)
    feedback_testcase = property(lambda x: x.feedback and x.feedback.testcase)
    feedback_answer_key = property(
        lambda x: x.feedback and x.feedback.answer_key)
    feedback_hint = property(lambda x: x.feedback_data.get('hint'))
    feedback_message = property(lambda x: x.feedback_data.get('message'))
    feedback_status = property(lambda x: x.feedback_data.get('status'))

    @lazy
    def answer_key(self):
        return self.question.answers.iospec(self.language)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'feedback' in kwargs:
            self.update_feedback(feedback=kwargs['feedback'])

    def __html__(self):
        return render_html(self.feedback)

    def clean(self):
        super().clean()
        if self.feedback:
            data = self.feedback.to_json()
            del data['grade']
            self.feedback_data = data

    def autograde_value(self):
        """
        Run code using the ejudge, saves the feedback and return the given
        grade.
        """

        # Compute feedback
        source = self.source
        language_ref = self.language.ejudge_ref()
        answer_key = self.answer_key
        feedback = grade_code(source, answer_key, lang=language_ref)

        # Save data and return grade
        self.update_feedback(feedback, update_grade=False)
        return self.feedback.grade * 100

    def update_feedback(self, feedback=None, update_grade=True):
        """
        Update feedback_data dictionary with info from feedback object
        """
        feedback = feedback or self.feedback

        self.feedback_data.update(
            answer_key=feedback.answer_key.to_json(),
            testcase=feedback.answer_key.to_json(),
            status=feedback.status,
        )
        if feedback.message:
            self.feedback_data['message'] = self.feedback.message
        if feedback.hint:
            self.feedback_data['hint'] = self.feedback.hint

        if update_grade:
            self.given_grade = feedback.grade * 100

        self.feedback = feedback
