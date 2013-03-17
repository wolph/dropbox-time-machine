import os
import time
import flask
import logging
import dropbox
import time_machine
import functools
import dropbox_flask_session
import forms
from dateutil import tz
import tasks
from main import app
import pytz

timezone = pytz.timezone(app.config.get('TIMEZONE', 'UTC'))

if app.debug:
    try:
        import flask_debugtoolbar
        toolbar = flask_debugtoolbar.DebugToolbarExtension(app)
    except ImportError:
        pass

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

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
    dropbox_session = context['dropbox_session']
    if dropbox_session.link() and dropbox_session.is_linked():
        return flask.redirect(flask.url_for('list_dropbox'))
    else:
        return flask.redirect(flask.url_for('authenticate'))


@app.route('/restore/', methods=['GET', 'POST'])
@view_decorator
def restore(context):
    if flask.session.get('request_token'):
        context['log'] = tasks.get_redis_log(dict(flask.session.items()))
    else:
        return flask.redirect(flask.url_for('authenticate'))


@app.route('/dropbox/', methods=['GET', 'POST'])
@app.route('/dropbox/<path:path>', methods=['GET', 'POST'])
@view_decorator
def list_dropbox(context, path=''):
    form = context['form'] = forms.RestoreForm(flask.request.form, path=path)

    try:
        tm = time_machine.TimeMachine(context['dropbox_session'])
        context['account'] = tm.account_info()
    except dropbox.rest.ErrorResponse, exception:
        if exception.status == 401:
            return flask.redirect(flask.url_for('authenticate'))
        else:
            raise

    context['path'] = path
    path_parts = context['path_parts'] = [('', 'Dropbox')]
    for part in os.path.split(path):
        if part:
            path_parts.append((os.path.join(path_parts[-1][0], part), part))

    context['parent_path'] = os.path.split(path)[0]
    metadata = context['metadata'] = tm.metadata(path)

    if metadata['is_dir']:
        for file in metadata.get('contents', []):
            file['name'] = os.path.split(file['path'])[-1]
            file['modified'] = file['modified'].astimezone(pytz.utc)
            file['title'] = 'Last modified: %s' % timezone.normalize(
                file['modified'])
    else:
        context['revisions'] = tm.revisions(path)

    if flask.request.method == 'POST' and form.validate():
        session = dict(flask.session.iteritems())
        app.logger.info(
            'Going to restore %r between %r and %r with session %r',
            form.path.data,
            form.start_date.data,
            form.end_date.data,
            session,
        )
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
    if force:
        # Make flask save the session again
        return flask.redirect(dropbox_session.link(force=force))
    elif flask.request.args.get('oauth_token'):
        # TODO: find a better way to do this, the Dropbox auth system is too
        # slow so we have to wait
        time.sleep(1)
        dropbox_session.link()
        return flask.redirect(flask.url_for('list_dropbox'))
    elif not dropbox_session.is_linked():
        context['url'] = flask.url_for('authenticate') + '?force=true'
    else:
        tm = time_machine.TimeMachine(dropbox_session)
        context['account'] = tm.account_info()

    # Make flask save the session again
    flask.session.permanent = True
    return context


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')

