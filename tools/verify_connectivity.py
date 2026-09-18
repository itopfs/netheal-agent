NAME = "verify_connectivity"
DESCRIPTION = "Run a full end-to-end connectivity verification test between two hosts. Always call this after a repair to confirm the fix worked before finishing."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "source": {"type": "string", "description": "Source host (e.g. pc1)"},
        "destination": {"type": "string", "description": "Destination host (e.g. server1)"},
    },
    "required": ["source", "destination"],
}


def execute(params: dict, simulator) -> str:
    return simulator.verify_connectivity(params["source"], params["destination"])
