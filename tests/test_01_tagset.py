from tagmania.iac_tools.tagset import TagSet


class TestTagSet:
    def test_init_empty(self):
        ts = TagSet()
        assert ts.to_list() == []

    def test_init_none(self):
        ts = TagSet(None)
        assert ts.to_list() == []

    def test_init_with_existing_tags(self):
        existing = [{"Key": "Name", "Value": "web-01"}]
        ts = TagSet(existing)
        assert ts.to_list() == existing

    def test_add_single_tag(self):
        ts = TagSet()
        ts.add("Environment", "production")
        assert ts.to_list() == [{"Key": "Environment", "Value": "production"}]

    def test_add_multiple_tags(self):
        ts = TagSet()
        ts.add("Name", "web-01")
        ts.add("Cluster", "prod")
        result = ts.to_list()
        assert len(result) == 2
        assert result[0] == {"Key": "Name", "Value": "web-01"}
        assert result[1] == {"Key": "Cluster", "Value": "prod"}

    def test_get_existing_key(self):
        ts = TagSet([{"Key": "Cluster", "Value": "staging"}])
        assert ts.get("Cluster") == "staging"

    def test_get_missing_key(self):
        ts = TagSet([{"Key": "Cluster", "Value": "staging"}])
        assert ts.get("NonExistent") is None

    def test_get_from_empty(self):
        ts = TagSet()
        assert ts.get("Anything") is None

    def test_get_first_match(self):
        ts = TagSet(
            [
                {"Key": "Name", "Value": "first"},
                {"Key": "Name", "Value": "second"},
            ]
        )
        assert ts.get("Name") == "first"

    def test_add_then_get(self):
        ts = TagSet()
        ts.add("Owner", "team-backend")
        assert ts.get("Owner") == "team-backend"

    def test_to_list_returns_internal_list(self):
        tags = [{"Key": "A", "Value": "1"}, {"Key": "B", "Value": "2"}]
        ts = TagSet(tags)
        assert ts.to_list() is tags

    def test_case_sensitive_keys(self):
        ts = TagSet([{"Key": "Name", "Value": "web"}])
        assert ts.get("Name") == "web"
        assert ts.get("name") is None
        assert ts.get("NAME") is None
