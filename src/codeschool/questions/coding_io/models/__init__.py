from iospec.feedback import Feedback
from codeschool.render import render_html as _render_html
from .question import CodingIoQuestion
from .answer_key import AnswerKey
from .submission import CodingIoSubmission

_render_html.register_template(Feedback, 'render/feedback.jinja2')