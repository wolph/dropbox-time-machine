#!/Users/rick/envs/dropbox/bin/python

import os
import dropbox
import logging
import rest
from datetime import datetime
from dateutil import parser, tz

logger = logging.getLogger(__name__)

TOKEN_FILE = 'token_store.txt'


class StoredSession(dropbox.session.DropboxSession):
    '''A wrapper around DropboxSession that stores a token to a file on disk
    '''

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('rest_client', rest.RESTClient)
        dropbox.session.DropboxSession.__init__(self, *args, **kwargs)
        self.load_token()

    def load_token(self):
        try:
            stored_token = open(TOKEN_FILE).read()
            self.set_token(*stored_token.split('|'))
        except IOError, e:
            logger.debug('Unable to get old token, not loading: %r', e)

    def write_token(self, token):
        f = open(TOKEN_FILE, 'w')
        f.write('|'.join([token.key, token.secret]))
        f.close()

    def delete_token(self):
        os.unlink(TOKEN_FILE)

    def link(self):
        request_token = self.obtain_request_token()
        url = self.build_authorize_url(request_token)
        print 'url:', url
        print '''Please authorize in the browser. After you're done, press''',
        print '''enter.'''
        raw_input()

        self.obtain_access_token(request_token)
        self.write_token(self.token)

    def unlink(self):
        self.delete_token()
        dropbox.session.DropboxSession.unlink(self)


class Metadata(object):

    def key_map(self, key, value):
        # Map the value by key
        mapper = self.KEY_MAPPING.get(key, lambda self, v: v)
        value = mapper(self, value)

        return self.type_map(value)

    def type_map(self, value):
        # Map the value by type
        mapper = self.TYPE_MAPPING.get(type(value), lambda self, v: v)
        value = mapper(self, value)

        return value

    def convert_timestamp(self, timestamp):
        return parser.parse(timestamp)

    def convert_list(self, list_):
        return MetadataList(list_)

    def convert_dict(self, dict_):
        return MetadataDict(dict_)

    KEY_MAPPING = {
        'modified': convert_timestamp,
        'client_mtime': convert_timestamp,
    }
    TYPE_MAPPING = {
        dict: convert_dict,
        list: convert_list,
    }


class MetadataDict(dict, Metadata):

    def __init__(self, metadata):
        for key, value in metadata.iteritems():
            self[key] = self.key_map(key, value)


class MetadataList(list, Metadata):

    def __init__(self, metadata):
        for value in metadata:
            self.append(self.type_map(value))


class TimeMachine(dropbox.client.DropboxClient):

    def revisions(self, path, rev_limit=5):
        revisions = dropbox.client.DropboxClient.revisions(
            self, path, rev_limit)
        revisions = MetadataList(revisions)

        return revisions

    def metadata(
            self, path, list=True, file_limit=25000, hash=None, rev=None,
            include_deleted=True):
        metadata = dropbox.client.DropboxClient.metadata(
            self, path, list, file_limit, hash, rev, include_deleted)
        metadata = MetadataDict(metadata)

        return metadata

    def restore(self, path, rev=None):
        if not rev:
            revisions = self.revisions(path)
            for revision in revisions:
                if 'is_deleted' not in revision:
                    rev = revision['rev']
                    break

        assert rev, 'Unable to find revision to restore'

        logger.info('Restoring %r to %r', path, rev)
        return dropbox.client.DropboxClient.restore(self, path, rev)

    def recursive_restore(self, path, start_date=None, end_date=None,
            yield_directories=False):
        logger.info(
            'Restoring files in %r which were deleted between %s and '
            '%s', path, start_date, end_date)
        metadata = self.metadata(path)
        # If no start date is given, default to some far in the past date
        # (should be enough as long as it's pre-1970)
        start_date = start_date or datetime(
            1950, 1, 1, 0, 0, 0, tz=tz.tzutc())

        # If no end date is given, default to now
        end_date = end_date or datetime.now(tz=tz.tzutc())

        for file in metadata.get('contents', []):
            if file['is_dir']:
                if yield_directories:
                    yield file
                else:
                    self.recursive_restore(file['path'], start_date, end_date)

            elif 'is_deleted' in file:
                if start_date <= file['modified'] <= end_date:
                    self.restore(file['path'])

