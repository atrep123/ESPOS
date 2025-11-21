import json
from pathlib import Path

from tools import npm_audit_to_sarif


def test_npm_audit_to_sarif_creates_rules_and_results(tmp_path: Path):
    audit_input = {
        "advisories": {
            "1001": {
                "module_name": "lodash",
                "title": "Prototype pollution",
                "severity": "critical",
                "overview": "Bad things",
                "url": "https://npmjs.com/advisories/1001",
            },
            "1002": {
                "module_name": "minimist",
                "title": "Arbitrary code exec",
                "severity": "moderate",
                "overview": "Also bad",
                "url": "https://npmjs.com/advisories/1002",
            },
        }
    }
    input_path = tmp_path / "npm_audit.json"
    output_path = tmp_path / "npm_audit.sarif"
    input_path.write_text(json.dumps(audit_input), encoding="utf-8")

    npm_audit_to_sarif.main([str(input_path), str(output_path)])

    sarif = json.loads(output_path.read_text(encoding="utf-8"))
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    results = sarif["runs"][0]["results"]

    assert {rule["id"] for rule in rules} == {"lodash", "minimist"}
    assert len(results) == 2

    level_map = {r["ruleId"]: r["level"] for r in results}
    # critical -> error, moderate -> warning
    assert level_map["lodash"] == "error"
    assert level_map["minimist"] == "warning"
