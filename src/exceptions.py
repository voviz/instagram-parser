class BaseParserException(Exception):
    """Base class for all parser errors"""

    def __str__(self):
        return 'Something goes wrong with parser'
