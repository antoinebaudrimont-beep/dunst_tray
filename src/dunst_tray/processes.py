"""Bounded /proc identities; no command lines, titles or message data.

Numeric foreign-user records are retained only to reject ambiguous ancestry;
executable identities are read for same-user foreground leaders only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    parent: int
    group: int
    tty: int
    foreground_group: int
    executable: str
    owner: int = field(default_factory=os.geteuid)


def process_snapshot(root: Path = Path("/proc"), limit: int = 8192):
    """Read only numeric stat fields and foreground leaders' executable names."""
    result = {}
    count = 0
    for directory in root.iterdir():
        if not directory.name.isdecimal():
            continue
        count += 1
        if count > limit:
            raise ValueError("Too many processes to validate safely")
        try:
            owner = directory.stat().st_uid
            raw = (directory / "stat").read_text()
            # comm may contain spaces/parentheses; it is deliberately discarded.
            fields = raw[raw.rfind(")") + 2:].split()
            parent, group, tty, foreground = (
                int(fields[index]) for index in (1, 2, 4, 5)
            )
            pid = int(directory.name)
            executable = ""
            if tty and pid == group == foreground and owner == os.geteuid():
                target = os.readlink(directory / "exe")
                if not target.endswith(" (deleted)"):
                    executable = Path(target).name
            result[pid] = ProcessIdentity(
                pid, parent, group, tty, foreground, executable, owner,
            )
        except (FileNotFoundError, ProcessLookupError):
            continue  # A process that has exited cannot own a current target.
        except (OSError, ValueError, IndexError):
            raise ValueError("Process ownership cannot be verified") from None
    return result


def descends_from(pid: int, ancestor: int, processes) -> bool:
    seen = set()
    for _ in range(64):
        if pid == ancestor:
            return True
        if pid in seen or pid not in processes:
            break
        seen.add(pid)
        pid = processes[pid].parent
    return False


def terminal_matches(window_pid: int, executable: str, processes) -> bool:
    """Require one foreground terminal session, led by the exact target binary.

    Multiple PTYs (tabs/tmux/server-owned windows) cannot identify the active
    terminal view safely. Background jobs and guessed command arguments never
    qualify. Multiple matching windows are rejected by the caller as usual.
    """
    if (window_pid not in processes or not executable
            or processes[window_pid].owner != os.geteuid()):
        return False
    leaders = [process for process in processes.values()
               if process.tty and process.pid == process.group
               == process.foreground_group
               and descends_from(process.pid, window_pid, processes)]
    return (len(leaders) == 1 and leaders[0].executable == executable
            and leaders[0].owner == os.geteuid())
