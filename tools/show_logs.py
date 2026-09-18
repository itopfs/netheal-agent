NAME = "show_logs"
DESCRIPTION = "Retrieve recent system log entries from a device. Reveals errors, warnings, and state-change events."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "device": {"type": "string", "description": "Device name (e.g. router1, switch1)"},
    },
    "required": ["device"],
}


def execute(params: dict, simulator) -> str:
    return simulator.show_logs(params["device"])
