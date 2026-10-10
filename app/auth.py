import hmac


def authorized(headers, expected):
    if not expected:
        return False
    values = [headers.get('x-api-key', '')]
    scheme, _, token = headers.get('authorization', '').partition(' ')
    if scheme.lower() == 'bearer':
        values.append(token)
    return any(hmac.compare_digest(value.encode('utf-8'), expected.encode('utf-8')) for value in values)
