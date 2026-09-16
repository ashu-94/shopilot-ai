class DomainError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "business_rule"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code
