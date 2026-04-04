from pathlib import Path


class Secret:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Secret(********)"

    def __str___(self):
        return "*******"


def pytest_configure(config):
    # Only configure pytest-html options when the plugin is active (--html flag passed)
    if hasattr(config.option, "self_contained_html"):
        project_root = Path(__file__).parent.parent
        css_file = project_root / "resources" / "pytest-html.css"
        config.option.css = [str(css_file)]
        if not config.option.self_contained_html:
            config.option.self_contained_html = True
