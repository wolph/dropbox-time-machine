import flask
import dropbox


class DropboxSession(dropbox.session.DropboxSession):

    def link(self, force=False, url=None):
        # Only build a new request token if we don't have one or are forced to
        # do so.
        if force or not self.request_token:
            print 'obtaining request token'
            self.obtain_request_token()
        else:
            try:
                print 'obtaining access token'
                self.obtain_access_token()
            except dropbox.rest.ErrorResponse, exception:
                if exception.status == 401:
                    #self.unlink()
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
        print 'building request token'
        request_token = dropbox.session.DropboxSession.obtain_request_token(
            self)

        flask.session['request_token'] = self.request_token.key
        flask.session['request_token_secret'] = self.request_token.secret
        return request_token

    def obtain_access_token(self, request_token=None):
        print 'building access token'
        '''
        This updates the DropboxSession so we have to notify Flask that our
        session has changed.
        '''
        access_token = dropbox.session.DropboxSession.obtain_access_token(
            self, request_token)

        flask.session['access_token'] = self.token.key
        flask.session['access_token_secret'] = self.token.secret
        return access_token

    def unlink(self):
        self.request_token = None
        flask.session['request_token'] = None
        flask.session['request_token_secret'] = None
        flask.session['access_token'] = None
        flask.session['access_token_secret'] = None
        return dropbox.session.DropboxSession.unlink(self)

    def __init__(self):
        from main import app
        dropbox.session.DropboxSession.__init__(
            self,
            consumer_key=app.config['APP_KEY'],
            consumer_secret=app.config['APP_SECRET'],
            access_type=app.config['ACCESS_TYPE'],
        )

        data = flask.session

        if data.get('request_token') and data.get('request_token_secret'):
            # Set the request token if available
            self.set_request_token(
                request_token=data['request_token'],
                request_token_secret=data['request_token_secret'],
            )

        if data.get('access_token') and data.get('access_token_secret'):
            # Set the access token if available
            self.set_token(
                access_token=data['access_token'],
                access_token_secret=data['access_token_secret'],
            )

