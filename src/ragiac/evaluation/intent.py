"""Functional-intent checks: does the generated Terraform actually do what the requirement asked?

`terraform validate` only proves the code is well-formed, and OPA only proves it obeys org
policy; neither proves it built the *right* thing (a valid, compliant config for the wrong
resource passes both). IaC-Eval addresses this with per-task intent specifications. This is a
lightweight equivalent: each task lists the resource types it must contain and attribute
assertions, evaluated against the parsed HCL.

Intent spec (JSON):
  {"resources": ["google_storage_bucket"],
   "attributes": [{"resource": "google_storage_bucket", "path": "versioning.enabled", "equals": true},
                  {"resource": "google_storage_bucket", "path": "lifecycle_rule.condition.age", "equals": 30}]}
`path` may also be a list of alternative paths (e.g. node_count | initial_node_count).
Constant arithmetic such as `30 * 24 * 60 * 60 * 1000` is evaluated before comparison, since a
model may legitimately write a number as an expression.
Operators: equals, one_of, contains (substring), gte, lte, exists, absent. String comparison is
case-insensitive. `resource` (and entries of `resources`) may be a list of alternatives, any one of
which satisfies the check — IAM, for instance, can legitimately be an _iam_member or _iam_binding.
"""

import ast
import operator
import re
from dataclasses import dataclass, field
from typing import Any

import hcl2


@dataclass(frozen=True)
class IntentResult:
    passed: bool
    failures: list[str] = field(default_factory=list)


def _unquote(value: Any) -> Any:
    if isinstance(value, str) and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _normalize(node: Any) -> Any:
    if isinstance(node, dict):
        return {_unquote(k): _normalize(v) for k, v in node.items() if k != "__is_block__"}
    if isinstance(node, list):
        return [_normalize(v) for v in node]
    return _unquote(node)


def parse_resources(hcl: str) -> dict[str, dict[str, dict]]:
    """Returns {resource_type: {resource_name: attributes}}."""
    parsed = _normalize(hcl2.loads(hcl))
    resources: dict[str, dict[str, dict]] = {}
    for block in parsed.get("resource", []):
        for rtype, instances in block.items():
            for name, attrs in instances.items():
                resources.setdefault(rtype, {})[name] = attrs
    return resources


def _values_at(node: Any, path: list[str]) -> list[Any]:
    # At the end of the path return the node untouched: a list here is a *value* (ports = ["22"]),
    # whereas a list mid-path is repeated blocks (hcl2 wraps every block in a list) to fan out over.
    if not path:
        return [node]
    if isinstance(node, list):
        return [v for item in node for v in _values_at(item, path)]
    if isinstance(node, dict) and path[0] in node:
        return _values_at(node[path[0]], path[1:])
    return []


_ARITHMETIC_RE = re.compile(r"^\$\{\s*[\d\s\*\+\-\/\(\)\.]+\s*\}$")
_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _eval_arithmetic(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_arithmetic(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval_arithmetic(node.left), _eval_arithmetic(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval_arithmetic(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    raise ValueError("unsupported expression")


def _coerce(value: Any) -> Any:
    """Resolve a `${ 30 * 24 * 60 }`-style constant expression to a number; leave everything else."""
    if isinstance(value, str) and _ARITHMETIC_RE.match(value):
        try:
            result = _eval_arithmetic(ast.parse(value[2:-1].strip(), mode="eval"))
            return int(result) if float(result).is_integer() else result
        except (ValueError, SyntaxError, ZeroDivisionError):
            return value
    return value


def _equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.lower() == expected.lower()
    return actual == expected


def _check_assertion(values: list[Any], spec: dict) -> bool:
    values = [_coerce(v) for v in values]
    if "exists" in spec:
        return bool(values) == bool(spec["exists"])
    if spec.get("absent"):
        return not values
    if "equals" in spec:
        return any(_equal(v, spec["equals"]) for v in values)
    if "one_of" in spec:
        return any(_equal(v, option) for v in values for option in spec["one_of"])
    if "contains" in spec:
        return any(isinstance(v, str) and str(spec["contains"]).lower() in v.lower() for v in values)
    if "gte" in spec:
        return any(isinstance(v, (int, float)) and v >= spec["gte"] for v in values)
    if "lte" in spec:
        return any(isinstance(v, (int, float)) and v <= spec["lte"] for v in values)
    return False


def check_intent(hcl: str, intent: dict | None) -> IntentResult:
    if not intent:
        return IntentResult(True)
    try:
        resources = parse_resources(hcl)
    except Exception as e:  # noqa: BLE001 - any parse failure means the intent can't be verified
        return IntentResult(False, [f"unparseable HCL: {type(e).__name__}"])

    failures: list[str] = []
    for entry in intent.get("resources", []):
        alternatives = [entry] if isinstance(entry, str) else list(entry)
        if not any(r in resources for r in alternatives):
            failures.append(f"missing resource type {' | '.join(alternatives)}")

    for spec in intent.get("attributes", []):
        alternatives = [spec["resource"]] if isinstance(spec["resource"], str) else list(spec["resource"])
        label = " | ".join(alternatives)
        paths = [spec["path"]] if isinstance(spec["path"], str) else list(spec["path"])
        path_label = " | ".join(paths)
        instances = [attrs for r in alternatives for attrs in resources.get(r, {}).values()]
        if not instances:
            failures.append(f"{label}.{path_label}: resource absent")
            continue
        # Satisfied if at least one instance of the resource type meets the assertion on any path.
        if not any(
            _check_assertion(_values_at(attrs, path.split(".")), spec) for attrs in instances for path in paths
        ):
            expected = {k: v for k, v in spec.items() if k not in ("resource", "path")}
            failures.append(f"{label}.{path_label} does not satisfy {expected}")

    return IntentResult(not failures, failures)
