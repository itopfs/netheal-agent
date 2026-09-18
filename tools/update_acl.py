NAME = "update_acl"
DESCRIPTION = "Add or remove an ACL rule on a firewall or router. Use to permit traffic that is being incorrectly blocked."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name (e.g. firewall)"},
        "action": {"type": "string", "enum": ["remove", "add"], "description": "Whether to add or remove a rule"},
        "rule_id": {"type": "string", "description": "ID of the rule to remove, or new rule details to add"},
    },
    "required": ["device", "action", "rule_id"],
}


def execute(params: dict, simulator) -> str:
    return simulator.update_acl(params["device"], params["action"], params["rule_id"])
