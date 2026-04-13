class AppException(Exception):
    """Base exception for application errors"""
    status_code = 500
    message = "An error occurred"
    
    def __init__(self, message=None):
        if message:
            self.message = message
        super().__init__(self.message)

class UniqueError(AppException):
    status_code = 409  # Conflict
    message = "Resource already exists"

class NotFoundError(AppException):
    status_code = 404
    message = "Resource not found"

class ValidationError(AppException):
    status_code = 400
    message = "Validation failed"

class ManualRaiseToTest(AppException):
    status_code = 400
    message = "Nothing actually goes wrong. We just want it to"

class AuthenticationError(AppException):
    status_code = 401
    message = "Authentication failed"

class AuthorizationError(AppException):
    status_code = 403
    message = "Permission denied"

class MissingFieldsError(AppException):
    status_code = 400
    message = "Missing Fields"

class DisabledAction(AppException):
    status_code = 403
    message = "That action is currently disabled"

class OuterServicesError(AppException):
    status_code = 500
    message = "OUTER SERVICES ERROR"