import sys
from mcp.server.fastmcp import FastMCP
import json
import os
from difflib import get_close_matches
from datetime import datetime
import logging

# Initialize MCP server
server = FastMCP(
    name="LockedRoomGame",
    host="0.0.0.0",
    port=8050
)

STATE_FILE = "state.json"
THOUGHTS_FILE = "thoughts.json"
SERVER_LOG_FILE = "server.log"

# Remove any existing logging handlers
if logging.getLogger().hasHandlers():
    logging.getLogger().handlers.clear()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

# Ensure thoughts log exists
if not os.path.exists(THOUGHTS_FILE):
    with open(THOUGHTS_FILE, 'w') as f:
        json.dump([], f)


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def log_thought_to_file(thought: str):
    """
    Append an agent's reasoning step to the thoughts log.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "thought": thought
    }
    try:
        with open(THOUGHTS_FILE, 'r+') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
    except FileNotFoundError:
        with open(THOUGHTS_FILE, 'w') as f:
            json.dump([entry], f, indent=4)


def match_object(name, objects):
    if name in objects:
        return name
    matches = get_close_matches(name, objects.keys(), n=1, cutoff=0.6)
    return matches[0] if matches else None


def log_tool_invocation(tool_name, **kwargs):
    """
    Log the invocation of a tool with its arguments.
    """
    logging.info(f"Tool invoked: {tool_name} | Args: {json.dumps(kwargs)}")


@server.tool()
async def look_around():
    log_tool_invocation("look_around")
    state = load_state()
    visible = []
    for name, data in state["objects"].items():
        if data.get("visible", False):
            visible.append({"name": name, "description": data.get("description", "")})
    return {"visible_objects": visible}


@server.tool()
async def inspect_object(object_name: str):
    log_tool_invocation("inspect_object", object_name=object_name)
    state = load_state()
    objects = state["objects"]
    key = match_object(object_name, objects)
    if not key:
        return {"error": f"No object named '{object_name}'."}
    obj = objects[key]
    if not obj.get("visible", False) and key not in state["player"]["inventory"]:
        return {"error": f"Object '{key}' is not accessible."}
    info = {"name": key, "description": obj.get("description", "")}
    if "locked" in obj:
        info["locked"] = obj.get("locked")
    if obj.get("openable") is not None:
        info["opened"] = obj.get("opened")
    return info


@server.tool()
async def take(object_name: str):
    log_tool_invocation("take", object_name=object_name)
    state = load_state()
    objects = state["objects"]
    key = match_object(object_name, objects)
    if not key:
        return {"success": False, "message": f"No object named '{object_name}'."}
    obj = objects[key]
    if not obj.get("visible", False):
        return {"success": False, "message": f"You can't see '{key}'."}
    if key in state["player"]["inventory"]:
        return {"success": False, "message": f"'{key}' already in inventory."}
    state["player"]["inventory"].append(key)
    obj["visible"] = False
    save_state(state)
    return {"success": True, "message": f"You take the {key}."}


@server.tool()
async def unlock(target: str, using: str):
    log_tool_invocation("unlock", target=target, using=using)
    state = load_state()
    objects = state["objects"]
    tgt = match_object(target, objects)
    if not tgt:
        return {"success": False, "message": f"No object named '{target}'."}
    obj = objects[tgt]
    if not obj.get("locked", False):
        return {"success": False, "message": f"{tgt} is not locked."}
    inv = state["player"]["inventory"]
    # Code unlock
    if "code_required" in obj:
        if using == obj["code_required"]:
            obj["locked"] = False
            save_state(state)
            return {"success": True, "message": f"You unlock the {tgt} with the code."}
        return {"success": False, "message": "Incorrect code."}
    # Key unlock
    if using not in inv:
        return {"success": False, "message": f"You don't have '{using}'."}
    if obj.get("key_required") == using:
        obj["locked"] = False
        save_state(state)
        return {"success": True, "message": f"You unlock the {tgt} with the {using}."}
    return {"success": False, "message": f"{using} can't unlock {tgt}."}


@server.tool()
async def open_object(object_name: str):
    log_tool_invocation("open_object", object_name=object_name)
    state = load_state()
    objects = state["objects"]
    key = match_object(object_name, objects)
    if not key:
        return {"success": False, "message": f"No object named '{object_name}'."}
    obj = objects[key]
    if obj.get("locked", False):
        return {"success": False, "message": f"{key} is locked."}
    if obj.get("opened", False):
        return {"success": False, "message": f"{key} is already open."}
    obj["opened"] = True
    for item in obj.get("contains", []):
        if item in objects:
            objects[item]["visible"] = True
    save_state(state)
    return {"success": True, "message": f"You open the {key} and find {', '.join(obj.get('contains', []))}."}


@server.tool()
async def read(object_name: str):
    log_tool_invocation("read", object_name=object_name)
    state = load_state()
    objects = state["objects"]
    key = match_object(object_name, objects)
    if not key:
        return {"success": False, "message": f"No object named '{object_name}'."}
    obj = objects[key]
    if not obj.get("readable", False):
        return {"success": False, "message": f"{key} is not readable."}
    if not obj.get("visible", False) and key not in state["player"]["inventory"]:
        return {"success": False, "message": f"You can't read '{key}' because you can't see it."}
    return {"success": True, "message": obj.get("content", "")}


@server.tool()
async def log_thought(message: str):
    log_tool_invocation("log_thought", message=message)
    """
    Log the agent's internal reasoning step to a JSON file.
    """
    log_thought_to_file(message)
    return {"logged": message}


# Run the server
if __name__ == "__main__":
    server.run(transport="sse")
