"""Raw ASGI guard checks auth before reading even one request-body byte."""
import json
from starlette.datastructures import Headers
from starlette.requests import Request
from app.auth import authorized
from app.errors import APIError, error_response
from app.schemas import problems

LIMITS = {'/predict': 1024 * 1024, '/predict/batch': 5 * 1024 * 1024, '/batch/jobs': 25 * 1024 * 1024}


class Guard:
    def __init__(self, app, api_key):
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        request_id = headers.get('x-request-id')

        async def send_echo(message):
            if message['type'] == 'http.response.start' and request_id:
                message['headers'] = list(message['headers']) + [(b'x-request-id', request_id.encode('latin-1'))]
            await send(message)

        path = scope['path']
        protected = path in LIMITS or path.startswith('/batch/jobs/')
        if protected and not authorized(headers, self.api_key):
            return await error_response(APIError(401, 'unauthorized', 'Missing or invalid API key.', headers={'WWW-Authenticate': 'Bearer'}))(scope, receive, send_echo)
        if path in LIMITS and scope['method'] == 'POST':
            if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                return await error_response(APIError(415, 'unsupported_media_type', 'Content-Type must be application/json.'))(scope, receive, send_echo)
            limit = LIMITS[path]
            try:
                length = int(headers.get('content-length', '0'))
            except ValueError:
                return await error_response(APIError(400, 'invalid_content_length', 'Invalid Content-Length.'))(scope, receive, send_echo)
            if length > limit:
                return await error_response(APIError(413, 'payload_too_large', 'Request body exceeds the endpoint limit.'))(scope, receive, send_echo)
            # Count streamed bodies too; Content-Length is never trusted alone.
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > limit:
                    return await error_response(APIError(413, 'payload_too_large', 'Request body exceeds the endpoint limit.'))(scope, receive, send_echo)
                if not message.get('more_body', False):
                    break
            sent = False
            original_receive = receive

            async def replay():
                nonlocal sent
                if not sent:
                    sent = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await original_receive()
            receive = replay
        await self.app(scope, receive, send_echo)


async def parse_request(request: Request, schema):
    try:
        def reject_constant(value):
            raise ValueError('Nonfinite JSON constant')
        value = json.loads((await request.body()).decode('utf-8'), parse_constant=reject_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise APIError(400, 'invalid_json', 'Request body must be valid UTF-8 JSON.')
    try:
        details = problems(schema, value)
    except RecursionError:
        raise APIError(422, 'validation_error', 'Request nesting is too deep.')
    if details:
        raise APIError(422, 'validation_error', 'Request does not match the official schema.', details)
    return value
