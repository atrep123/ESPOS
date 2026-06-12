from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "uiflow" / "dial" / "blocks"
SOURCE = BLOCKS / "alpha2" / "PropTx.py"
MANIFEST = BLOCKS / "prop_tx.json"
OUT = BLOCKS / "dist" / "PropTx.m5b2"


METHODS = [
    {
        "name": "__init__",
        "label": "%1 Prop init TX %2 RX %3",
        "kind": "statement",
        "params": [
            {"name": "tx", "type": "int", "default": "13", "field": "number", "min": "0", "max": "48"},
            {"name": "rx", "type": "int", "default": "15", "field": "number", "min": "0", "max": "48"},
        ],
    },
    {"name": "preview", "label": "Prop PREVIEW %1 colors %2", "kind": "statement", "params": [
        {"name": "colors", "type": "list", "default_code": "[]"}
    ]},
    {"name": "fire", "label": "Prop ODPAL %1 colors %2", "kind": "statement", "params": [
        {"name": "colors", "type": "list", "default_code": "[]"}
    ]},
    {"name": "stop", "label": "Prop STOP %1", "kind": "statement", "params": []},
    {"name": "arm", "label": "Prop ARM %1", "kind": "statement", "params": []},
    {"name": "remote_led", "label": "Prop remote LED %1 which %2", "kind": "statement", "params": [
        {"name": "which", "type": "int", "default": "3", "field": "number", "min": "3", "max": "5"},
    ]},
    {"name": "sync_palette", "label": "Prop sync palette %1 colors %2", "kind": "statement", "params": [
        {"name": "colors", "type": "list", "default_code": "[]"}
    ]},
    {"name": "reply", "label": "Prop reply %1", "kind": "value", "params": []},
    {"name": "hue_color", "label": "Prop hue %1 deg %2 to color", "kind": "value", "params": [
        {"name": "deg", "type": "int", "default": "0", "field": "number", "min": "0", "max": "359"},
    ]},
    {"name": "default_hues", "label": "Prop default hues %1", "kind": "value", "params": []},
    {"name": "default_colors", "label": "Prop default colors %1", "kind": "value", "params": []},
    {"name": "palette_from_hues", "label": "Prop colors from hues %1 hues %2", "kind": "value", "params": [
        {"name": "hues", "type": "list", "default_code": "[0, 120, 240, 210, 60]"}
    ]},
    {"name": "set_color", "label": "Prop set color %1 colors %2 LED %3 color %4", "kind": "value", "params": [
        {"name": "colors", "type": "list", "default_code": "[]"},
        {"name": "index", "type": "int", "default": "1", "field": "number", "min": "1", "max": "5"},
        {"name": "color", "type": "tuple", "default_code": "(255, 0, 0)"},
    ]},
    {"name": "first_four", "label": "Prop first four %1 colors %2", "kind": "value", "params": [
        {"name": "colors", "type": "list", "default_code": "[]"}
    ]},
    {"name": "rgb_color", "label": "Prop RGB %1 R %2 G %3 B %4", "kind": "value", "params": [
        {"name": "r", "type": "int", "default": "255", "field": "number", "min": "0", "max": "255"},
        {"name": "g", "type": "int", "default": "0", "field": "number", "min": "0", "max": "255"},
        {"name": "b", "type": "int", "default": "0", "field": "number", "min": "0", "max": "255"},
    ]},
    {"name": "rgb888", "label": "Prop RGB888 %1 color %2", "kind": "value", "params": [
        {"name": "color", "type": "tuple", "default_code": "(255, 0, 0)"}
    ]},
    {"name": "remote_led3", "label": "Prop remote LED3 %1", "kind": "statement", "params": []},
    {"name": "remote_led5", "label": "Prop remote LED5 %1", "kind": "statement", "params": []},
]


def block_type(method: str) -> str:
    return f"custom_proptx_{'init' if method == '__init__' else method}"


def msg_key(method: str) -> str:
    return f"CUSTOM_PROPTX_{'INIT' if method == '__init__' else method.upper()}"


def value_default(param: dict[str, str]) -> str:
    if "default_code" in param:
        return param["default_code"]
    if "default" in param:
        return param["default"]
    return "None"


def method_sources(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    lines = source.splitlines()
    prop_tx = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PropTx")
    sources: dict[str, str] = {}
    for method in [node for node in prop_tx.body if isinstance(node, ast.FunctionDef)]:
        body = list(method.body)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        if not body:
            sources[method.name] = ""
            continue
        start = min(node.lineno for node in body) - 1
        end = max(node.end_lineno or node.lineno for node in body)
        sources[method.name] = "\n".join(lines[start:end])
    return sources


def member_data(method: dict[str, object], sources: dict[str, str]) -> dict[str, object]:
    params = []
    for param in method["params"]:
        item = {
            "name": param["name"],
            "type": param.get("type"),
            "default": param.get("default"),
            "note": {},
            "field": param.get("field", ""),
        }
        if "max" in param:
            item["max"] = param["max"]
        if "min" in param:
            item["min"] = param["min"]
        params.append(item)
    return {
        "name": method["name"],
        "note": {},
        "label": {"en": method["label"]},
        "params": params,
        "return": "",
        "source": sources[method["name"]],
        "ast_return": {"code": None, "id": None},
        "doc_return": None,
    }


def js_value_line(param: dict[str, str]) -> str:
    name = param["name"]
    default = json.dumps(value_default(param))
    return (
        f"  var {name} = Blockly.Python.valueToCode(block, '{name}', "
        f"Blockly.Python.ORDER_FUNCTION_CALL) || {default};"
    )


def build_jscode(category: str, color: str) -> str:
    languages = {msg_key(method["name"]): {"en": method["label"]} for method in METHODS}
    parts = [
        "const CUSTOM_PROPTX_LANGUAGES = " + json.dumps(languages, indent=2) + ";",
        "",
        "const initType = 'custom_proptx_init';",
        "Blockly.BlockRegExpList['custom_proptx'] = {",
        "  regexp: new RegExp(/^custom_proptx_/),",
        '  code: "from PropTx import PropTx",',
        "  initBlockType: initType,",
        "  categoryId: 'custom_proptx',",
        "}",
        "Blockly.utils.registerLanguages(CUSTOM_PROPTX_LANGUAGES)",
        "",
        f"Blockly.Msg.CUSTOM_PROPTX_HUE = '{color}'",
        f"Blockly.Msg.CUSTOM_PROPTX = '{category}'",
        "",
        "Blockly.utils.getcustom_proptxOptions = function() {",
        "  let options = [];",
        "  let list = Blockly.utils.getCustomNameList(initType);",
        "  for (let i = 0; i < list.length; i++) {",
        "    let value = list[i];",
        "    options.push([String(value), String(value)]);",
        "  }",
        "  if (options.length === 0) return [",
        "    ['proptx_0', 'proptx_0']",
        "  ];",
        "  return options;",
        "}",
        "",
    ]

    for method in METHODS:
        name = method["name"]
        block = block_type(name)
        params = method["params"]
        args = []
        if name == "__init__":
            args.append(
                "{\n"
                "          'type': 'field_input',\n"
                "          'name': 'NAME',\n"
                "          'text': 'proptx_0'\n"
                "        }"
            )
        else:
            args.append(
                "{\n"
                "          'type': 'field_dropdown',\n"
                "          'name': 'NAME',\n"
                "          'options': Blockly.utils.getcustom_proptxOptions\n"
                "        }"
            )
        for param in params:
            args.append(
                "{\n"
                "          'type': 'input_value',\n"
                f"          'name': '{param['name']}'\n"
                "        }"
            )
        args_text = ",\n        ".join(args)
        connection = (
            "      'previousStatement': null,\n      'nextStatement': null,"
            if method["kind"] == "statement"
            else "      'output': null,"
        )
        parts.extend([
            f'Blockly.Blocks["{block}"] = {{',
            "  init: function() {",
            "    this.jsonInit(this._init());",
            "  },",
            "  _init: function() {",
            "    return {",
            f"      'message0': Blockly.Msg.{msg_key(name)},",
            "      'args0': [",
            f"        {args_text},",
            "      ],",
            connection,
            "      'inputsInline': true,",
            f"      'colour': \"{color}\",",
            '      "tool": []',
            "    };",
            "  }",
            "}",
            "",
            f'Blockly.Python["{block}"] = function(block) {{',
            "  var varname = block.getFieldValue('NAME') || '_';",
        ])
        parts.extend(js_value_line(param) for param in params)
        arg_names = [param["name"] for param in params]
        call_name = "PropTx" if name == "__init__" else name
        if name == "__init__":
            parts.append('  return varname + " = PropTx(" + tx + ", " + rx + ")\\n";')
        else:
            joined = ' + ", " + '.join(arg_names)
            if arg_names:
                call = f'varname + ".{call_name}(" + {joined} + ")"'
            else:
                call = f'varname + ".{call_name}()"'
            if method["kind"] == "statement":
                parts.append(f'  return {call} + "\\n";')
            else:
                parts.append(f"  return [{call}, Blockly.Python.ORDER_NONE];")
        parts.extend(["}", ""])
    return "\n".join(parts).rstrip()


def toolbox_shadow(param: dict[str, str]) -> str:
    default = value_default(param)
    if param.get("field") == "number" or param.get("type") == "int":
        return (
            f'  <value name="{param["name"]}">\n'
            '    <shadow type="math_number">\n'
            f'      <field name="NUM">{default}</field>\n'
            "    </shadow>\n"
            "  </value>"
        )
    if param.get("type") in {"list", "tuple"}:
        return f'  <value name="{param["name"]}"/>'
    return (
        f'  <value name="{param["name"]}">\n'
        '    <shadow type="text">\n'
        '      <field name="TEXT"/>\n'
        "    </shadow>\n"
        "  </value>"
    )


def build_toolbox(category: str, color: str) -> str:
    blocks = []
    for method in METHODS:
        block = block_type(method["name"])
        shadows = "\n".join(toolbox_shadow(param) for param in method["params"])
        if shadows:
            blocks.append(f'<block type="{block}">\n{shadows}\n</block>')
        else:
            blocks.append(f'<block type="{block}"/>')
    return (
        f'\n<category name="{category}" colour="{color}" hidden="true" toolboxitemid="custom_proptx">\n'
        '<title text="PropTx" docsLink="https://github.com/atrep123/m5-prop-lora"></title>\n'
        + "".join(blocks)
        + "\n</category>\n"
    )


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    sources = method_sources(source)
    missing = [method["name"] for method in METHODS if method["name"] not in sources]
    if missing:
        raise SystemExit(f"missing methods in {SOURCE}: {missing}")

    category = manifest["category"]
    color = manifest["color"]
    data = {
        "category": category,
        "color": color,
        "uiflow2": {
            "jscode": build_jscode(category, color),
            "toolbox": build_toolbox(category, color),
            "toolboxitemid": "custom_proptx",
            "block_type": [block_type(method["name"]) for method in METHODS],
        },
        "data": {
            "name": "PropTx",
            "note": {"en": "Prop TX UIFlow2 bridge for the authenticated prop_frame sender."},
            "details": {
                "color": color,
                "link": "https://github.com/atrep123/m5-prop-lora",
                "image": "",
                "category": "Custom",
            },
            "header": {
                "file": "PropTx",
                "time": "2026-06-10",
                "author": "",
                "email": "",
                "license": "MIT License",
            },
            "assignments": [],
            "example": "",
            "source_internal": "",
            "source_external": "",
            "members": [member_data(method, sources) for method in METHODS],
            "python_file_name": "PropTx",
        },
        "pyCode": source,
        "version": "alpha2",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(METHODS)} Alpha-2 blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
