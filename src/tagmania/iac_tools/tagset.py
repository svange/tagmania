# A wrapper for tags

class TagSet:
    def __init__ (self, tags=None):
        if tags == None:
            self._tags = []
        else:
            self._tags = tags

    def add (self, key, value):
        tag = { 'Key': key, 'Value': value }
        self._tags.append(tag)

    def get (self, key):
        for tag in self._tags:
            if tag['Key'] == key:
                return tag['Value']
        return None

    def to_list (self):
        return self._tags
