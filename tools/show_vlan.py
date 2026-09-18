NAME = "show_vlan"
DESCRIPTION = "Display VLAN table and port VLAN assignments on a switch. Use to identify VLAN misconfigurations."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Switch device name (e.g. switch1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_vlan(params["device"])
