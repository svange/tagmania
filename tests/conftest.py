from pathlib import Path


class Secret:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Secret(********)"

    def __str___(self):
        return "*******"

def pytest_configure(config):
    # compute the CSS file’s absolute path from this file’s location
    project_root = Path(__file__).parent.parent
    css_file = project_root / "resources" / "pytest-html.css"
    # override whatever was in addopts
    config.option.css = [str(css_file)]

    # ensure we’re still inlining it into the HTML
    if not config.option.self_contained_html:
        config.option.self_contained_html = True
