import re

from ..exceptions.http_exceptions import bad_request_exception


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,128}$")


def validate_password_strength(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise bad_request_exception(
            "Password must be 8-128 characters and include uppercase, lowercase, number, and special character"
        )
