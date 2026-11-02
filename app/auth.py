import hmac

from fastapi import HTTPException, Request


def require_api_key(request: Request) -> None:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    expected = request.app.state.settings.api.api_key.get_secret_value()
    if scheme != "Bearer" or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")
