VALID_TOKEN = "valid-token"


def validate_bearer_token(authorization: str) -> bool:
    scheme, _, token = authorization.partition(" ")
    return scheme.lower() == "bearer" and token == VALID_TOKEN
