import json
import logging
import sys
import uuid
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


def npm_severity_to_sarif(sev):
    mapping = {
        'critical': 'error',
        'high': 'error',
        'moderate': 'warning',
        'low': 'note',
    }
    return mapping.get(sev, 'note')

def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) < 2:
        logging.error('Usage: npm_audit_to_sarif.py <npm_audit.json> <output.sarif>')
        sys.exit(1)
    with open(argv[0], 'r', encoding='utf-8-sig') as f:
        npm_data = json.load(f)
    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "npm audit",
                        "informationUri": "https://docs.npmjs.com/cli/v8/commands/npm-audit",
                        "rules": []
                    }
                },
                "results": []
            }
        ]
    }
    rules = {}
    results = []
    advisories = npm_data.get('advisories', {})
    for adv_id, adv in advisories.items():
        rule_id = adv.get('module_name', str(adv_id))
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": adv.get('title', rule_id),
                "shortDescription": {"text": adv.get('title', '')},
                "fullDescription": {"text": adv.get('overview', '')},
                "helpUri": adv.get('url', ''),
                "properties": {"severity": adv.get('severity', '')}
            }
        result = {
            "ruleId": rule_id,
            "level": npm_severity_to_sarif(adv.get('severity', 'low')),
            "message": {"text": adv.get('title', '')},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "package-lock.json"},
                        "region": {"startLine": 1}
                    }
                }
            ],
            "properties": {
                "advisoryId": adv_id,
                "module": adv.get('module_name', ''),
                "severity": adv.get('severity', ''),
                "url": adv.get('url', '')
            }
        }
        results.append(result)
    sarif['runs'][0]['tool']['driver']['rules'] = list(rules.values())
    sarif['runs'][0]['results'] = results
    with open(argv[1], 'w', encoding='utf-8') as f:
        json.dump(sarif, f, indent=2)
    logging.info("npm audit SARIF written to %s (rules=%d, results=%d)", argv[1], len(rules), len(results))

if __name__ == '__main__':
    main()
