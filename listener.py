"""Program that listens to wayfire and send pipe updates to waybar.

Code is messy as it is only a prototype.
Everything works as I am expecting them to work.
"""

from os import listdir, makedirs, mkfifo, remove
import time

from utility import (
    base_dir,
    get_active_workspace_number,
    get_all_active_workspaces_numbers,
    SOCKET,
    get_window_title,
    get_workspace_number_safely,
    update_fifo,
)

SOCKET.watch()

# create a fifo pipe
# ----------------------
makedirs(base_dir, exist_ok=True)
# clean pipes if exists
for pipe in listdir(base_dir):
    remove(f"{base_dir}/{pipe}")
# create pipes
pipes = [f"workspace{num}" for num in range(1, 10)] + ["window_title"]
for pipe in pipes:
    mkfifo(f"{base_dir}/{pipe}", 0o600)

all_active_workspaces_copy = get_all_active_workspaces_numbers()
previous_active_workspace = get_active_workspace_number()
previous_title = None
timer = 0

debug = False
# debug = True

# plugin state
expo_state = False


def refresh_workspaces():
    """Refresh all workspaces."""
    global previous_title
    global all_active_workspaces_copy
    all_copy_set = set(all_active_workspaces_copy)
    current_set = set(get_all_active_workspaces_numbers())
    get_current_active_window_title = get_window_title()
    for workspace in current_set:
        if workspace == previous_active_workspace:
            if get_current_active_window_title != previous_title:
                update_fifo(
                    window_title=get_current_active_window_title,
                    active="active",
                    who="refresh_workspaces: refresh window title",
                    debug=debug,
                )
                previous_title = get_current_active_window_title

            update_fifo(
                workspace=previous_active_workspace,
                active="active",
                who="refresh_workspaces: refresh active workspace",
                debug=debug,
            )
        else:
            update_fifo(
                workspace=workspace,
                active="inactive",
                who="refresh_workspaces: refresh inactive workspace",
                debug=debug,
            )

    # remove previous active workspace that became inactive
    for workspace in all_copy_set - current_set:
        update_fifo(
            workspace=workspace,
            active="hidden",
            who="refresh_workspaces: remove inactive workspace",
            debug=debug,
        )

    # get all current active workspaces
    all_active_workspaces_copy = get_all_active_workspaces_numbers()


while True:
    timer = time.time()
    msg = SOCKET.read_next_event()
    if "new-workspace" in msg:
        workspace_coordinates = msg["new-workspace"]
        x, y = workspace_coordinates.get("x", -1), workspace_coordinates.get("y", -1)
        current_workspace_number = get_workspace_number_safely(x, y)
        all_active_workspaces_numbers = get_all_active_workspaces_numbers()
        all_active_workspaces_copy = all_active_workspaces_numbers.copy()

        # update current active workspace
        update_fifo(
            workspace=current_workspace_number,
            active="active",
            who="new-workspace: new active workspace",
            debug=debug,
        )

        # update previous active workspace
        if previous_active_workspace != current_workspace_number:
            if previous_active_workspace not in all_active_workspaces_numbers:
                update_fifo(
                    workspace=previous_active_workspace,
                    active="hidden",
                    who="new-workspace: previous workspace hidden",
                    debug=debug,
                )
            else:
                update_fifo(
                    workspace=previous_active_workspace,
                    active="inactive",
                    who="new-workspace: previous workspace inactive",
                    debug=debug,
                )

        previous_active_workspace = current_workspace_number

    # trigger expo plugin event where moving active view to another workspace
    elif "view-workspace-changed" in msg.get("event") and expo_state is True:
        from_workspace_coordinates = msg.get("from")
        to_workspace_coordinates = msg.get("to")

        # skip if no changes made, usually active view or windows
        # was moved inside the workpace only
        if from_workspace_coordinates == to_workspace_coordinates:
            continue

        from_workspace_number = get_workspace_number_safely(
            from_workspace_coordinates.get("x", -1),
            from_workspace_coordinates.get("y", -1),
        )
        to_workspace_number = get_workspace_number_safely(
            to_workspace_coordinates.get("x", -1), to_workspace_coordinates.get("y", -1)
        )

        all_active_workspaces_numbers = get_all_active_workspaces_numbers()
        all_active_workspaces_copy = all_active_workspaces_numbers.copy()

        # update from workspace and to workspace
        if from_workspace_number not in all_active_workspaces_numbers:
            update_fifo(
                workspace=from_workspace_number,
                active="hidden",
                who="view-workspace-changed: from workspace hidden",
                debug=debug,
            )

        if to_workspace_number in all_active_workspaces_numbers:
            if to_workspace_number != previous_active_workspace:
                update_fifo(
                    workspace=to_workspace_number,
                    active="inactive",
                    who="view-workspace-changed: to workspace inactive",
                    debug=debug,
                )

    # if moved by grid when it was outside it's own workspace
    # this bug indicates that if the view has a little bit appearance on
    # another workspace, it will become and active view workspace
    # moving it out or tiled it needs to refresh those active views again
    # and remove the inactive workspace if exists
    elif "view-tiled" in msg.get("event"):
        refresh_workspaces()

    if "view" in msg:
        if (
            msg["view"]
            and "title" in msg["view"]
            and msg.get("event")
            in [
                "view-focused",
                "view-title-changed",
            ]  # might add more if needed but view-focused plugin is helping a lot
        ):
            title = msg["view"]["title"]

            if title == previous_title:
                end_timer = time.time()
                time_result = end_timer - timer
                # print(time_result, time_result < 1 and title == previous_title)
                continue

            if title.strip():
                # send to fifo
                # print("new title", title, msg.get("event"))
                update_fifo(
                    window_title=title,
                    active="active",
                    who="title-changed: new title",
                    debug=debug,
                )
                previous_title = title
        else:
            previous_title = None
            # see events for all views
            # print(
            #     "-" * 10, msg["event"], msg["view"]["title"] if msg["view"] else "None"
            # )
            if msg["view"] is None:
                # print("No Window title")
                # send to fifo
                update_fifo(
                    window_title=None,
                    active="hidden",
                    who="title-changed: no window title",
                    debug=debug,
                )

    if debug:
        print("-" * 10, msg.get("event"))

    if msg.get("event") == "plugin-activation-state-changed":
        if msg.get("plugin") == "expo":
            expo_state = msg.get("state")
