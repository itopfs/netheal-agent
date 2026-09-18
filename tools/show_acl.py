NAME = "show_acl"
DESCRIPTION = "Display Access Control List (ACL/firewall) rules on a device. Use to identify traffic being blocked."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name (e.g. firewall, router1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_acl(params["device"])
