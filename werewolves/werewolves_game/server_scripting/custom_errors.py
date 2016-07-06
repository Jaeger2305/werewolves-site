class ContinueError(Exception):
    """Raise an error that continues execution but with some parameters replaced with defaults"""
    def __init__(self, message, error_dict=None, default_dict=None):
        super(ContinueError, self).__init__(message)

        self.error_dict = error_dict
        self.default_dict= default_dict