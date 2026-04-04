from tagmania.iac_tools.filterset import FilterSet


class TestFilterSet:
    def test_init_empty(self):
        fs = FilterSet()
        assert fs.to_list() == []

    def test_init_none(self):
        fs = FilterSet(None)
        assert fs.to_list() == []

    def test_init_with_existing_filters(self):
        existing = [{"Name": "tag:Cluster", "Values": ["prod"]}]
        fs = FilterSet(existing)
        assert fs.to_list() == existing

    def test_add_string_value_wraps_to_list(self):
        fs = FilterSet()
        fs.add("tag:Cluster", "production")
        result = fs.to_list()
        assert len(result) == 1
        assert result[0] == {"Name": "tag:Cluster", "Values": ["production"]}

    def test_add_list_value(self):
        fs = FilterSet()
        fs.add("instance-state-name", ["running", "stopped"])
        result = fs.to_list()
        assert result[0] == {"Name": "instance-state-name", "Values": ["running", "stopped"]}

    def test_add_multiple_filters(self):
        fs = FilterSet()
        fs.add("tag:Cluster", "prod")
        fs.add("instance-state-name", "running")
        assert len(fs.to_list()) == 2

    def test_get_existing_filter(self):
        fs = FilterSet()
        fs.add("tag:Cluster", ["web", "api"])
        assert fs.get("tag:Cluster") == ["web", "api"]

    def test_get_missing_filter(self):
        fs = FilterSet()
        fs.add("tag:Cluster", "prod")
        assert fs.get("tag:Environment") is None

    def test_get_from_empty(self):
        fs = FilterSet()
        assert fs.get("anything") is None

    def test_get_first_match(self):
        fs = FilterSet(
            [
                {"Name": "tag:Cluster", "Values": ["first"]},
                {"Name": "tag:Cluster", "Values": ["second"]},
            ]
        )
        assert fs.get("tag:Cluster") == ["first"]

    def test_to_list_returns_internal_list(self):
        filters = [{"Name": "tag:A", "Values": ["1"]}]
        fs = FilterSet(filters)
        assert fs.to_list() is filters
