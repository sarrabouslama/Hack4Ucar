"""
Custom exceptions
"""


class Hack4UcarException(Exception):
    """Base exception for Hack4Ucar application"""

    pass


class ValidationError(Hack4UcarException):
    """Validation error exception"""

    pass


class NotFoundError(Hack4UcarException):
    """Resource not found exception"""

    pass


class AuthenticationError(Hack4UcarException):
    """Authentication error exception"""

    pass
