NAME = "finish"
DESCRIPTION = "Signal that the incident is fully resolved. ONLY call this after verify_connectivity confirms the fix worked."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "description": "One-sentence explanation of the root cause"},
        "summary": {"type": "string", "description": "Brief summary of what was done to fix the issue"},
    },
    "required": ["reason", "summary"],
}


def execute(params: dict, simulator) -> str:
    return f"Incident closed.\nRoot cause: {params.get('reason', '')}\nFix: {params.get('summary', '')}"
