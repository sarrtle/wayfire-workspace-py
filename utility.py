"""One big application to control wayfire with python."""

import json
import subprocess
from sys import argv
from typing import Literal
from wayfire import WayfireSocket
from wayfire.extra.ipc_utils import WayfireUtils


SOCKET = WayfireSocket()
UTILS_SOCKET = WayfireUtils(SOCKET)


def get_active_workspace_number():
    """Get the current active workspace number.

    Note:
        Assuming this is following the 3x3 grid and the workspace
        number is hardcoded into it.

    """
    active_workspace_number = UTILS_SOCKET.get_active_workspace_number()

    if isinstance(active_workspace_number, int):
        return active_workspace_number

    else:
        subprocess.call(
            [
                "notify-send",
                "-t",
                "1000",
                "-u",
                "critical",
                "IPC Script",
                "Failed to get active workspace number",
            ]
        )
        return 0


def get_workspace_number_safely(workspace_x: int, workspace_y: int):
    """Get the workspace number safely using coordinates."""
    num = UTILS_SOCKET.get_workspace_number(workspace_x, workspace_y)
    if not isinstance(num, int):
        subprocess.call(
            [
                "notify-send",
                "-t",
                "1000",
                "-u",
                "critical",
                "IPC Script",
                "Failed to get workspace number",
            ]
        )
        return 0
    return num


def get_all_active_workspaces_numbers() -> list[int]:
    """Get all active workspace numbers."""
    active_workspace_data = UTILS_SOCKET.get_workspaces_with_views()

    if not active_workspace_data:
        return []

    # simple validation that doesn't require pydantic
    if "x" not in active_workspace_data[0] and "y" not in active_workspace_data[0]:
        subprocess.call(
            [
                "notify-send",
                "-t",
                "1000",
                "-u",
                "critical",
                "IPC Script",
                "Failed to get all active workspace numbers",
            ]
        )
        return [0]

    active_workspace_numbers = [
        get_workspace_number_safely(awd["x"], awd["y"]) for awd in active_workspace_data
    ]

    if 0 in active_workspace_numbers:
        subprocess.call(
            [
                "notify-send",
                "-t",
                "1000",
                "-u",
                "critical",
                "IPC Script",
                "Failed to get some of the active workspace number",
            ]
        )

    return active_workspace_numbers


def get_window_title() -> str:
    """Get the title of the focused window."""
    title = UTILS_SOCKET.get_focused_view_title()
    if not isinstance(title, str) and title is not None:
        subprocess.call(
            [
                "notify-send",
                "-t",
                "1000",
                "-u",
                "critical",
                "IPC Script",
                "Failed to get window title",
            ]
        )
        return "error"

    return title[:20] if title else title or ""


base_dir = "/tmp/pyscript_waybar_modules"


def update_fifo(
    workspace: int | None = None,
    active: Literal["active", "inactive", "hidden"] | None = None,
    window_title: str | None = None,
    who: str | None = None,
    debug: bool = False,
):
    """Update fifo."""
    if (
        workspace is not None
        and debug is True
        or window_title is not None
        and debug is True
    ):
        print(
            "written---",
            "workspace:",
            workspace,
            "window-title:",
            window_title,
            active,
            "-- who:",
            who,
        )

    # don't update if workspace is 0, came from errors
    if workspace is not None and workspace != 0:
        fifo_path = f"{base_dir}/workspace{workspace}"
        with open(fifo_path, "w") as fifo:
            fifo.write(
                json.dumps(
                    {
                        "text": "" if active == "hidden" else str(workspace),
                        "class": active,
                    }
                )
            )
            fifo.flush()
    else:
        fifo_path = f"{base_dir}/window_title"
        with open(fifo_path, "w") as fifo:
            fifo.write(
                json.dumps(
                    {
                        "text": (
                            str(window_title)[:20] + "..."
                            if len(str(window_title)) > 20
                            else window_title or ""
                        ),
                        "class": active,
                    }
                )
            )
            fifo.flush()


def force_refresh_all_workspace(debug: bool = False):
    """Refresh the workspaces."""
    current_active_workspace = get_active_workspace_number()
    update_fifo(
        workspace=current_active_workspace,
        active="active",
        who="force_refresh_all_workspace: refresh active workspace",
        debug=debug,
    )
    all_active_workspaces = get_all_active_workspaces_numbers()
    for workspace in all_active_workspaces:
        if workspace == current_active_workspace:
            continue

        update_fifo(
            workspace=workspace,
            active="inactive",
            who="force_refresh_all_workspace: refresh inactive workspace",
            debug=debug,
        )

    # hide workspace if they dont exist on
    # all active workspaces
    for workspace in range(1, 10):
        if (
            workspace not in all_active_workspaces
            and workspace != current_active_workspace
        ):
            update_fifo(
                workspace=workspace,
                active="hidden",
                who="force_refresh_all_workspace: refresh hidden workspace",
                debug=debug,
            )

    # update window title
    window_title = get_window_title()
    update_fifo(
        window_title=window_title,
        active="active" if window_title else "hidden",
        who="force_refresh_all_workspace: refresh window title",
        debug=debug,
    )


def go_to_workspace(workspace: int):
    """Go to workspace."""
    # no move occur on same active workspace
    if workspace == get_active_workspace_number():
        return

    if workspace > 9 or workspace < 1:
        subprocess.call(
            [
                "notify-send",
                "-t",
                "1000",
                "-u",
                "critical",
                "IPC Script",
                "Failed to go to workspace",
            ]
        )
        return

    # assuming 3x3
    mapping = {
        1: {"x": 0, "y": 0},
        2: {"x": 1, "y": 0},
        3: {"x": 2, "y": 0},
        4: {"x": 0, "y": 1},
        5: {"x": 1, "y": 1},
        6: {"x": 2, "y": 1},
        7: {"x": 0, "y": 2},
        8: {"x": 1, "y": 2},
        9: {"x": 2, "y": 2},
    }
    SOCKET.set_workspace(mapping[workspace]["x"], mapping[workspace]["y"])


def main():
    """Application to run."""
    if argv[1] == "get_active_workspace_number":
        print(get_active_workspace_number())
    elif argv[1] == "get_all_active_workspaces_numbers":
        print(get_all_active_workspaces_numbers())
    elif argv[1] == "get_window_title":
        print(get_window_title())
    elif argv[1] == "get_all_data_except_title":
        data = {
            "current_active_workspace": get_active_workspace_number(),
            "all_active_workspaces": get_all_active_workspaces_numbers(),
        }
        print(json.dumps(data))
    elif argv[1] == "force_refresh_all_workspace":
        force_refresh_all_workspace()
    elif argv[1] == "go_to_workspace":
        if len(argv) == 3 and argv[2].isdigit():
            workspace = int(argv[2])
            go_to_workspace(workspace)
        else:
            subprocess.call(
                [
                    "notify-send",
                    "-t",
                    "1000",
                    "-u",
                    "critical",
                    "IPC Script",
                    "Failed to go to workspace",
                ]
            )


if __name__ == "__main__":
    main()
