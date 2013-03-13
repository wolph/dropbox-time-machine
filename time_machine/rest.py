import dropbox

class ErrorResponse(Exception):
    def __init__(self, exception):
        # Copy all variables from the original exception
        self.__dict__.update(exception.__dict__)

    def __repr__(self):
        return '<%s>' % self

class RESTClientObject(dropbox.rest.RESTClientObject):
    def request(self, *args, **kwargs):
        try:
            response = dropbox.rest.RESTClientObject.request(
                self, *args, **kwargs)
        except dropbox.rest.ErrorResponse, e:
            raise ErrorResponse(e)

        return response

class RESTClient(dropbox.rest.RESTClient):
    IMPL = RESTClientObject()

