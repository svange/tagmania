# A wrapper for filters

class FilterSet:
    def __init__ (self, filters=None):
        if filters == None:
            self._filters = []
        else:
            self._filters = filters

    def add (self, name, values):
        if isinstance(values, str):
            values = [values]
        f = { 'Name': name, 'Values': values }
        self._filters.append(f)

    def get (self, name):
        for f in self._filters:
            if f['Name'] == name:
                return f['Values']
        return None

    def to_list (self):
        return self._filters
