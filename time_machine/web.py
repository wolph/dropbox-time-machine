import os
import flask
import time_machine
import functools
import dropbox_flask_session
import forms
from dateutil import tz
from celery import Celery
import settings
from redish.client import Client
import tasks

base_path = os.path.abspath(os.path.join(__file__, '..', '..'))
app = flask.Flask(
    __name__,
    static_folder=os.path.join(base_path, 'static'),
    template_folder=os.path.join(base_path, 'templates'),
)
app.config.from_pyfile('settings.py')

celery = Celery()
celery.config_from_object(settings)

redis = Client()


def view_decorator(f):

    @functools.wraps(f)
    def _view_decorator(*args, **kwargs):
        context = dict(dropbox_session=dropbox_flask_session.DropboxSession())
        ret = f(context, *args, **kwargs)

        if not ret or isinstance(ret, dict):
            return flask.render_template('%s.html' % f.__name__, **context)
        else:
            return ret

    return _view_decorator


@app.route('/')
@view_decorator
def index(context):
    if context['dropbox_session'].is_linked():
        return flask.redirect(flask.url_for('list_dropbox'))
    else:
        return flask.redirect(flask.url_for('authenticate'))


@app.route('/restore/', methods=['GET', 'POST'])
@view_decorator
def restore(context):
    context['log'] = tasks.get_redis_log(dict(flask.session.items()))


@app.route('/dropbox/', methods=['GET', 'POST'])
@app.route('/dropbox/<path:path>', methods=['GET', 'POST'])
@view_decorator
def list_dropbox(context, path=''):
    form = context['form'] = forms.RestoreForm(flask.request.form, path=path)

    tm = time_machine.TimeMachine(context['dropbox_session'])
    context['account'] = tm.account_info()

    context['path'] = path
    path_parts = context['path_parts'] = [('', 'Dropbox')]
    for part in os.path.split(path):
        if part:
            path_parts.append((os.path.join(path_parts[-1][0], part), part))

    context['parent_path'] = os.path.split(path)[0]
    metadata = context['metadata'] = tm.metadata(path)
    for file in metadata['contents']:
        file['name'] = os.path.split(file['path'])[-1]
        file['title'] = 'Last modified: %s' % (file['modified'].astimezone(
            tz.tzlocal()))

    if flask.request.method == 'POST' and form.validate():
        session = dict(flask.session.iteritems())
        tasks.restore.delay(
            session=session,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            path=form.path.data,
        )

        flask.flash(
            'Your files will be restored in the background, please be patient')

        return flask.redirect(flask.url_for('restore'))

    return context


@app.route('/authenticate/')
@view_decorator
def authenticate(context):
    dropbox_session = context['dropbox_session']

    force = flask.request.args.get('force')

    if not dropbox_session.is_linked() or force:
        # Make flask save the session again
        context['url'] = dropbox_session.link(force=force)
    else:
        tm = time_machine.TimeMachine(dropbox_session)
        context['account'] = tm.account_info()

    # Make flask save the session again
    flask.session.permanent = True
    return context


if __name__ == '__main__':
    app.run()

