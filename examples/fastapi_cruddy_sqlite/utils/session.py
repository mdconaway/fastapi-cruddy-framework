from fastapi.requests import HTTPConnection


def get_client_identity(connection: HTTPConnection):
    token_value = connection.session.get("token")
    return str(token_value) if token_value is not None else None
