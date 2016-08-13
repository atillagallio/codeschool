from django.dispatch import Signal


#: This signal is emitted when a submission finishes its autograde() method
#: successfully and sets the Submission status to STATUS_DONE.
autograde_signal = Signal(providing_args=['submission', 'given_grade'])


#: This signal is emitted when a response completes the manual grading process
manual_grade_signal = Signal(providing_args=['submission', 'given_grade'])
