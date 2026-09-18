NAME = "add_route"
DESCRIPTION = "Add a static IP route to a router's routing table. Use when a destination network is unreachable due to a missing route."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Router name (e.g. router1)"},
        "network": {"type": "string", "description": "Destination network in CIDR notation (e.g. 10.0.2.0/24)"},
        "via": {"type": "string", "description": "Next-hop IP address"},
        "interface": {"type": "string", "description": "Outbound interface (e.g. Gi0/1)"},
    },
    "required": ["device", "network", "via", "interface"],
}


def execute(params: dict, simulator) -> str:
    return simulator.add_route(params["device"], params["network"], params["via"], params["interface"])
