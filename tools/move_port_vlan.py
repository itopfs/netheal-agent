NAME = "move_port_vlan"
DESCRIPTION = "Reassign a switch port to a different VLAN. Use when a host is isolated due to a wrong VLAN assignment."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Switch name (e.g. switch1)"},
        "port": {"type": "string", "description": "Port identifier (e.g. Fa0/1)"},
        "vlan": {"type": "integer", "description": "Target VLAN ID"},
    },
    "required": ["device", "port", "vlan"],
}


def execute(params: dict, simulator) -> str:
    return simulator.move_port_vlan(params["device"], params["port"], params["vlan"])
