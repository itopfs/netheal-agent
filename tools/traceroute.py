NAME = "traceroute"
DESCRIPTION = (
    "Trace the network path hop-by-hop to a destination. "
    "'source' is optional — omit it to trace from the management server. "
    "Only set 'source' to a network device you can SSH into (router, switch, firewall). "
    "Never use an end-user device (pc1, workstation) as source — if it is unreachable, the tool cannot run from it."
)
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "source": {
            "type": "string",
            "description": "Network device to trace from (e.g. router1). Omit to trace from the management server.",
        },
        "destination": {
            "type": "string",
            "description": "Destination device name or IP (e.g. server1 or 10.0.2.100)",
        },
    },
    "required": ["destination"],
}


def execute(params: dict, simulator) -> str:
    source = params.get("source", "mgmt")
    return simulator.traceroute(source, params["destination"])
