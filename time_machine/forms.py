from wtforms import validators
from wtforms.ext.dateutil import fields as date_fields
import wtforms
import datetime
from dateutil import tz


class GreaterThan(object):
    '''
    Compares the value of two fields the value of self is to be greater than
    the supplied field.

    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    '''

    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(field.gettext(
                u'Invalid field name %r.') % self.fieldname)

        if field.data != '' and field.data < other.data:
            d = {
                'other_name': other.label.text,
                'self_name': field.label.text,
            }
            if self.message is None:
                self.message = field.gettext(
                    u'%(self_name)s must be greater than %(other_name)s.')

            raise validators.ValidationError(self.message % d)


class Delta(object):
    '''
    Compares the value of two fields the value of abs(self-other) is to be
    between min and max (inclusive).

    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    :param min_
        The minimum difference.
    :param max_:
        The maximum difference.
    '''

    def __init__(self, fieldname, message=None, min_=0, max_=None):
        self.fieldname = fieldname
        self.message = message
        self.min_ = min_
        self.max_ = max_

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise validators.ValidationError(field.gettext(
                u'Invalid field name %r.') % self.fieldname)

        if field.data == '' or other.data == '':
            # If there's nothing to validate, don't try
            return

        if not self.min_ <= abs(field.data - other.data) <= self.max_:
            d = {
                'self_name': field.label.text,
                'other_name': other.label.text,
                'min_': self.min_,
                'max_': self.max_ or 'infinity',
            }
            if self.message is None:
                self.message = field.gettext(
                    u'The difference between %(other_name)s and '
                    '%(self_name)s must be between %(min_)s and %(max_)s')

            raise validators.ValidationError(self.message % d)

def _now():
    return datetime.datetime.now(tz=tz.tzlocal())

def _one_day_ago():
    return _now() - datetime.timedelta(days=1)


class ReadOnlyTextInput(wtforms.widgets.TextInput):

    def __call__(self, field, **kwargs):
        kwargs.setdefault('readonly', True)
        return wtforms.widgets.TextInput.__call__(self, field, **kwargs)


class RestoreForm(wtforms.Form):
    start_date = date_fields.DateTimeField(default=_one_day_ago)
    end_date = date_fields.DateTimeField(
        default=_now,
        validators=[
            GreaterThan('start_date'),
            Delta(
                'start_date',
                'For security reasons the maximum allowed interval is 1 day',
                min_=datetime.timedelta(days=0),
                max_=datetime.timedelta(days=1),
            ),
        ],
    )
    path = wtforms.fields.StringField(
        widget=ReadOnlyTextInput(),
    )

