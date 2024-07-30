class Error(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class ConnectionError(Error):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class OSError(Error):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class BufferError(Error):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
