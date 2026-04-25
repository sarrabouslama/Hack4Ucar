"""
Shared utilities across modules
"""


def format_response(data: dict, message: str = "Success") -> dict:
    """Format API response"""
    return {
        "status": "success",
        "message": message,
        "data": data,
    }


def format_error(error_message: str, error_code: str = "ERROR") -> dict:
    """Format API error response"""
    return {
        "status": "error",
        "code": error_code,
        "message": error_message,
    }
