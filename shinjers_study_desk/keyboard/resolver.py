"""
Conflict-resolution logic for Keybind Remapper.

Kept free of any Qt/Anki imports so it can be tested with plain Python.
Keys passed in here are expected to already be normalized strings
(e.g. "Ctrl+Z", "J", "@"), so plain string comparison is enough.
"""

SWAP = "swap"      # displaced action takes the key the new owner left behind
SPARE = "spare"    # displaced action takes the first free key from spare_keys
DELETE = "delete"  # displaced action is simply unbound
POLICIES = (SWAP, SPARE, DELETE)


def parse_keys(value, norm):
    """Turn a config value ("j", ["j", "Left"], "", null) into normalized keys.

    Raises ValueError for keys Qt can't understand.
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, list):
        raise ValueError(f"expected a key string or a list of keys, got {value!r}")
    keys = []
    for raw in value:
        if not isinstance(raw, str) or not raw.strip():
            continue
        # A literal space is a valid key; anything else gets trimmed.
        key = norm(raw if raw == " " else raw.strip())
        if not key:
            raise ValueError(f"'{raw}' is not a key Anki understands")
        if key not in keys:
            keys.append(key)
    return keys


def translate_names(current, wanted):
    """Resolve "key:X" names to whichever action currently holds key X.

    Returns (translated_wanted, errors).
    """
    holder = {}
    for name, keys in current.items():
        for key in keys:
            holder.setdefault(key, name)
    out, errors = {}, []
    for name, keys in wanted.items():
        if name.startswith("key:"):
            real = holder.get(name[4:])
            if real is None:
                errors.append(f"'{name}': nothing is currently bound to {name[4:]}")
                continue
            name = real
        if name not in current:
            errors.append(f"'{name}' is not a known action here")
            continue
        out[name] = keys
    return out, errors


def resolve(
    current,
    wanted,
    policy=SWAP,
    spare_keys=(),
    reserved=(),
    avoid=(),
    reserved_label="another shortcut",
):
    """Apply the wanted bindings on top of the current ones.

    current:    {action: [keys]}  what is bound right now
    wanted:     {action: [keys]}  what the user asked for (names must exist in current)
    reserved:   keys owned by something outside this group that must win over
                unconfigured actions here
    avoid:      keys that must not be handed out to displaced actions
    reserved_label: how to describe the owner of a reserved key in notes
    Returns (result, notes, errors) where result is {action: [keys]} in the
    same order as current, and notes is {action: "what happened"}.
    """
    reserved, avoid = set(reserved), set(avoid)
    result, notes, errors = {}, {}, []

    # 1. Configured actions get exactly what they asked for.
    claimed_by = {}
    for name, keys in wanted.items():
        kept = []
        for key in keys:
            if key in claimed_by:
                errors.append(
                    f"{key} is assigned to both '{claimed_by[key]}' and '{name}'; "
                    f"keeping it on '{claimed_by[key]}'"
                )
                continue
            claimed_by[key] = name
            kept.append(key)
        result[name] = kept
        if kept != current[name]:
            notes[name] = "changed by you" if kept else "unbound by you"

    freed = {
        name: [k for k in current[name] if k not in claimed_by and k not in reserved]
        for name in wanted
    }
    in_use = set(claimed_by) | reserved

    # 2. Everything else keeps whatever keys nobody took from it.
    displaced = []
    for name, keys in current.items():
        if name in wanted:
            continue
        keep = [k for k in keys if k not in claimed_by and k not in reserved]
        lost = [k for k in keys if k not in keep]
        result[name] = keep
        in_use.update(keep)
        if lost:
            displaced.append((name, lost))

    # 3. Find new homes for actions whose keys were taken.
    for name, lost in displaced:
        takers = ", ".join(
            f"'{claimed_by[k]}'" if k in claimed_by else reserved_label for k in lost
        )
        lost_str = ", ".join(lost)
        if result[name]:
            notes[name] = f"lost {lost_str} to {takers}, still has {', '.join(result[name])}"
            continue
        if policy == DELETE:
            notes[name] = f"unbound: {lost_str} was taken by {takers}"
            continue

        new_key = None
        if policy == SWAP:
            for key in lost:
                for cand in freed.get(claimed_by.get(key), []):
                    if cand not in in_use and cand not in avoid:
                        new_key = cand
                        break
                if new_key:
                    break
        if new_key is None:
            for cand in spare_keys:
                if cand not in in_use and cand not in avoid:
                    new_key = cand
                    break

        if new_key is None:
            notes[name] = f"unbound: {lost_str} was taken by {takers} and no free key was left"
        else:
            result[name] = [new_key]
            in_use.add(new_key)
            notes[name] = f"moved {lost_str} -> {new_key} ({lost_str} taken by {takers})"

    ordered = {name: result[name] for name in current}
    return ordered, notes, errors
