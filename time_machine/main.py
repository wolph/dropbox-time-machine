import os
import flask
import logging
from logging import handlers
from redish.client import Client

base_path = os.path.abspath(os.path.join(__file__, '..', '..'))
app = flask.Flask(
    __name__,
    static_folder=os.path.join(base_path, 'static'),
    template_folder=os.path.join(base_path, 'templates'),
)
app.config.from_pyfile('settings.py')

redis = Client()

if app.config.get('ADMINS') and not app.debug:
    mail_handler = handlers.SMTPHandler(
        app.config.get('SMTP_SERVER', '127.0.0.1'),
        app.config.get('SERVER_EMAIL', app.config['ADMINS'][0]),
        app.config['ADMINS'],
        'Dropbox Time Machine Error',
    )

    mail_handler.setFormatter(logging.Formatter('''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    '''))

    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

if not app.debug:
    syslog_handler = handlers.SysLogHandler()
    syslog_handler.setLevel(logging.WARNING)
    app.logger.addHandler(syslog_handler)

