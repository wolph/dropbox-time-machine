import flask
import dropbox


class DropboxSession(dropbox.session.DropboxSession):

    def __init__(self, session=None):
        from main import app
        dropbox.session.DropboxSession.__init__(
            self,
            consumer_key=app.config['APP_KEY'],
            consumer_secret=app.config['APP_SECRET'],
            access_type=app.config['ACCESS_TYPE'],
        )

        session = self.session = session or flask.session
        if session.get('request_token') and session.get(
                'request_token_secret'):
            # Set the request token if available
            self.set_request_token(
                request_token=session['request_token'],
                request_token_secret=session['request_token_secret'],
            )

        if session.get('access_token') and session.get('access_token_secret'):
            # Set the access token if available
            self.set_token(
                access_token=session['access_token'],
                access_token_secret=session['access_token_secret'],
            )

    def link(self, force=False, url=None):
        # Only build a new request token if we don't have one or are forced to
        # do so.
        if force or not self.request_token:
            self.obtain_request_token()
        else:
            try:
                self.obtain_access_token()
            except dropbox.rest.ErrorResponse, exception:
                if exception.status == 401:
                    pass
                else:
                    raise

        return self.build_authorize_url(
            self.request_token, url or flask.request.base_url)

    def obtain_request_token(self):
        '''
        This updates the DropboxSession so we have to notify Flask that our
        session has changed.
        '''
        request_token = dropbox.session.DropboxSession.obtain_request_token(
            self)

        self.session['request_token'] = self.request_token.key
        self.session['request_token_secret'] = self.request_token.secret
        return request_token

    def obtain_access_token(self, request_token=None):
        '''
        This updates the DropboxSession so we have to notify Flask that our
        session has changed.
        '''
        access_token = dropbox.session.DropboxSession.obtain_access_token(
            self, request_token)

        self.session['access_token'] = self.token.key
        self.session['access_token_secret'] = self.token.secret
        return access_token

    def unlink(self):
        self.request_token = None
        self.session['request_token'] = None
        self.session['request_token_secret'] = None
        self.session['access_token'] = None
        self.session['access_token_secret'] = None
        return dropbox.session.DropboxSession.unlink(self)

