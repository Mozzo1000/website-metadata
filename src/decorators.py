def require_icons(func):
    def _decorator(self, *args, **kwargs):
        if self.icons:
            return func(self, *args, **kwargs)
        else:
            return None
    return _decorator