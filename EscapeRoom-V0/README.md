# 🗝️ EscapeRoom-V0

**EscapeRoom-V0** is a simple environment simulating a locked-room escape.  
The player is an AI agent that must interact with the environment to find a way out.

---

## 🎯 Objective

Escape the locked room by exploring, discovering tools and clues, and unlocking the exit door secured with a keypad.

---

## 🕹️ Available Actions

The environment exposes a number of tools (actions), implemented as Python functions.  
Each action is decorated with `@server.tool` in the server code.

Some example actions include:

- `look_around` — Observe the surroundings in the room.
- `inspect(object)` — Examine an object for more detail.
- `take(object)` — Pick up an object.
- `open(target)` — Attempt to open something (e.g., a box).
- `read(object)` — Read an object like a note or label.
- `use(item, target)` — Use one item with another (e.g., use key on box).

*For the full list, see the server code.*

---

## 🧩 Suggested Escape Path

A typical escape sequence may look like this:

1. `look_around` → Find a key.
2. `inspect("drawer")` → Locate the key.
3. `take("key")`
4. `use("key", "box")` → Open the box.
5. `take("note")`
6. `read("note")` → Learn the keypad code.
7. `open("door", code=<from_note>)`
8. Escape!

---

## 🔍 Code Reference

All available actions are defined in the server under functions decorated with:

```python
@server.tool
def action(...):
    ...
