from starlette.responses import JSONResponse
from app.schemas import validate


class APIError(Exception):
    def __init__(self, status, code, message, details=None, headers=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers or {}


def error_response(error):
    body = {'error': {'code': error.code, 'message': error.message}}
    if error.details is not None:
        body['error']['details'] = error.details
    validate('ErrorResponse', body)
    return JSONResponse(body, status_code=error.status, headers=error.headers)
