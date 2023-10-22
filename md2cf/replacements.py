import importlib.util
import json
import re
from typing import List

from md2cf.console_output import console


class Replacement:
    def __init__(
        self, name: str, pattern: str, new_value: str, evaluate: bool = False
    ) -> None:
        self.name = name
        self.pattern = pattern
        self.new_value = new_value
        self.evaluate = evaluate

    def replace(self, page):
        console.print(f"Performing replacement '{self.name}'")
        if self.evaluate:
            new_value = eval(self.new_value)
        else:
            new_value = self.new_value
        page.body, count = re.subn(f"({self.pattern})", new_value, page.body)
        console.print(f">> {count} replacements made")
        return page

    def __repr__(self) -> str:
        return self.name


def create_replacements(replacements, replacementfile: str) -> List[Replacement]:
    result = []
    commandline_replacements = (
        [item for sublist in replacements for item in sublist] if replacements else []
    )

    # Create Replacement objects for the commandline replacements
    for i, r in enumerate(commandline_replacements):
        result.append(Replacement(f"CLI replacement {i}", *r.split("=", 1)))

    # Opt out if no file specified
    if not replacementfile:
        return result

    file_replacements = json.load(open(replacementfile))
    # Do we need to load any modules?
    for env in file_replacements.get("environment", []):
        if env.get("import"):
            spec = importlib.util.spec_from_file_location(
                env["import"], env.get("path")
            )
            globals()[env["import"]] = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(globals()[env["import"]])

    # Get the replacement definitions
    for i, r in enumerate(file_replacements["replacements"]):
        new_value = r["new_value"]
        if isinstance(new_value, list):
            new_value = "\n".join(new_value)
        result.append(
            Replacement(
                r.get("name", f"File replacement {i}"),
                r["pattern"],
                new_value,
                r.get("evaluate", False),
            )
        )

    return result
