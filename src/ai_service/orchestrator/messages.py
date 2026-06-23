from enum import Enum

class SystemMessage(str, Enum):
    ERR_PROVIDER_TIMEOUT = "Sorry, the AI provider took too long to respond."
    ERR_PROVIDER_FAILED = "Sorry, I am currently unavailable to process this request."
    ERR_MAX_TURNS = "I took too many steps to answer this. Please try asking in a different way."
    ERR_PERMISSION_DENIED = "Permission denied. Your access was revoked before confirmation."
    MSG_ACTION_CANCELLED = "Action cancelled."
    MSG_CONFIRM_ACTION = "Please confirm the action: {tool_name} with {args}"
