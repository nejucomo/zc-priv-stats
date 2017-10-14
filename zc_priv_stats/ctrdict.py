class CounterDict (dict):
    def __getitem__(self, key):
        return self.get(key, 0)

    def __setitem__(self, key, value):
        assert type(value) is int, (key, value)
        if value == 0:
            self.pop(key, None)
        else:
            dict.__setitem__(self, key, value)
