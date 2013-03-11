import time_machine
import dropbox_flask_session
import dropbox
import celery
from datetime import datetime


def get_redis_log(session):
    from web import redis
    return redis.List('log_%s' % session['request_token'])


def get_redis_logger(session):
    redis_log = get_redis_log(session)

    def log(message, *args, **kwargs):
        redis_log.append('%s: %s' % (
            datetime.now(),
            message % (args or kwargs),
        ))

    return log


@celery.task
def restore(session, start_date, end_date, path):
    dropbox_session = dropbox_flask_session.DropboxSession(session)
    tm = time_machine.TimeMachine(dropbox_session)
    logger = restore.get_logger()
    log = get_redis_logger(session)

    restore_sub = restore.s(
        session=session, start_date=start_date, end_date=end_date)
    restore_file_sub = restore_file.s(session=session)

    log('Restoring files in %r', path)

    logger.info(
        'Restoring files in %r which were deleted between %s and '
        '%s', path, start_date, end_date)

    try:
        metadata = tm.metadata(path)
    except dropbox.rest.ErrorResponse, exception:
        if exception.status == 404:
            log.error('Unable to list %r', path)
            logger.error(
                'Unable to list %r, exception: %r', path, exception)
            return

        elif exception.status == 503:
            try:
                retry_after = int(exception.headers['Retry-After'])
            except:
                # Hasn't occured yet so I don't have any data on what Dropbox
                # really returns here, if we actually get this problem we can
                # solve it more specifically
                retry_after = 60

            log('Too many requests, sleeping for %d seconds', retry_after)
            logger.error(
                'Too many requests, sleeping for %d seconds', retry_after)
            raise restore.retry(exception, countdown=retry_after)

    for dir in metadata.get('contents', []):
        if dir['is_dir']:
            restore_sub.delay(path=dir['path'])

    for file in metadata.get('contents', []):
        if not file['is_dir'] and start_date <= file['modified'] <= end_date:
            restore_file_sub.delay(file=file)


@celery.task
def restore_file(session, file):
    log = get_redis_logger(session)
    dropbox_session = dropbox_flask_session.DropboxSession(session)
    tm = time_machine.TimeMachine(dropbox_session)
    restored_file = tm.restore(file['path'])

    log('Restored %s', restored_file['path'])

