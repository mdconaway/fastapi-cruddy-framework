from fastapi import Request, WebSocket


def get_client_identity(connection: Request | WebSocket):
    token_value = connection.session.get("token")
    return str(token_value) if token_value is not None else None
