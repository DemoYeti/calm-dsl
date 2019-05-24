import time
import warnings
from pprint import pprint
import json
from json import JSONEncoder

import arrow
import click
from prettytable import PrettyTable
from anytree import NodeMixin, RenderTree

from .utils import get_name_query, get_states_filter, highlight_text
from .constants import APPLICATION, RUNLOG


def get_apps(obj, name, filter_by, limit, offset, quiet, all_items):
    client = obj.get("client")
    config = obj.get("config")

    params = {"length": limit, "offset": offset}
    filter_query = ""
    if name:
        filter_query = get_name_query([name])
    if filter_by:
        filter_query = filter_query + ";" + filter_by if name else filter_by
    if all_items:
        filter_query += get_states_filter(APPLICATION.STATES, state_key="_state")
    if filter_query.startswith(";"):
        filter_query = filter_query[1:]

    if filter_query:
        params["filter"] = filter_query

    res, err = client.application.list(params=params)

    if err:
        pc_ip = config["SERVER"]["pc_ip"]
        warnings.warn(UserWarning("Cannot fetch blueprints from {}".format(pc_ip)))
        return

    table = PrettyTable()
    table.field_names = [
        "Application Name",
        "Source Blueprint",
        "State",
        "Owner",
        "Created On",
    ]
    json_rows = res.json()["entities"]

    if quiet:
        for _row in json_rows:
            row = _row["status"]
            click.echo(highlight_text(row["name"]))
        return

    table = PrettyTable()
    table.field_names = [
        "NAME",
        "SOURCE BLUEPRINT",
        "STATE",
        "OWNER",
        "CREATED ON",
        "LAST UPDATED",
        "UUID",
    ]
    for _row in json_rows:
        row = _row["status"]
        metadata = _row["metadata"]

        creation_time = int(metadata["creation_time"]) // 1000000
        last_update_time = int(metadata["last_update_time"]) // 1000000

        table.add_row(
            [
                highlight_text(row["name"]),
                highlight_text(row["resources"]["app_blueprint_reference"]["name"]),
                highlight_text(row["state"]),
                highlight_text(metadata["owner_reference"]["name"]),
                highlight_text(time.ctime(creation_time)),
                "{}".format(arrow.get(last_update_time).humanize()),
                highlight_text(row["uuid"]),
            ]
        )
    click.echo(table)


def _get_app(client, app_name, all=False):
    # 1. Get app_uuid from list api
    params = {"filter": "name=={}".format(app_name)}
    if all:
        params["filter"] += get_states_filter(APPLICATION.STATES, state_key="_state")

    res, err = client.application.list(params=params)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    response = res.json()
    entities = response.get("entities", None)
    app = None
    if entities:
        if len(entities) != 1:
            raise Exception("More than one app found - {}".format(entities))

        # click.echo(">> {} found >>".format(app_name))
        app = entities[0]
    else:
        raise Exception(">> No app found with name {} found >>".format(app_name))
    app_id = app["metadata"]["uuid"]

    # 2. Get app details
    click.echo(">> Fetching app details")
    res, err = client.application.read(app_id)
    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))
    app = res.json()
    return app


def describe_app(obj, app_name):
    client = obj.get("client")
    app = _get_app(client, app_name, all=True)

    click.echo("\n----Application Summary----\n")
    app_name = app["metadata"]["name"]
    click.echo(
        "Name: "
        + highlight_text(app_name)
        + " (uuid: "
        + highlight_text(app["metadata"]["uuid"])
        + ")"
    )
    click.echo("Status: " + highlight_text(app["status"]["state"]))
    click.echo(
        "Owner: " + highlight_text(app["metadata"]["owner_reference"]["name"]), nl=False
    )
    click.echo(
        " Project: " + highlight_text(app["metadata"]["project_reference"]["name"])
    )

    click.echo(
        "Blueprint: "
        + highlight_text(app["status"]["resources"]["app_blueprint_reference"]["name"])
    )

    created_on = int(app["metadata"]["creation_time"]) // 1000000
    past = arrow.get(created_on).humanize()
    click.echo(
        "Created: {} ({})".format(
            highlight_text(time.ctime(created_on)), highlight_text(past)
        )
    )

    click.echo(
        "Application Profile: "
        + highlight_text(
            app["status"]["resources"]["app_profile_config_reference"]["name"]
        )
    )

    deployment_list = app["status"]["resources"]["deployment_list"]
    click.echo("Deployments [{}]:".format(highlight_text((len(deployment_list)))))
    for deployment in deployment_list:
        click.echo(
            "\t {} {}".format(
                highlight_text(deployment["name"]), highlight_text(deployment["state"])
            )
        )

    action_list = app["status"]["resources"]["action_list"]
    click.echo("App Actions [{}]:".format(highlight_text(len(action_list))))
    for action in action_list:
        action_name = action["name"]
        if action_name.startswith("action_"):
            prefix_len = len("action_")
            action_name = action_name[prefix_len:]
        click.echo("\t" + highlight_text(action_name))

    variable_list = app["status"]["resources"]["variable_list"]
    click.echo("App Variables [{}]".format(highlight_text(len(variable_list))))
    for variable in variable_list:
        click.echo(
            "\t{}: {}  # {}".format(
                highlight_text(variable["name"]),
                highlight_text(variable["value"]),
                highlight_text(variable["label"]),
            )
        )

    click.echo(
        "# Hint: You can run actions on the app using: calm app {} <action_name>".format(
            app_name
        )
    )


class RunlogNode(NodeMixin):
    def __init__(self, runlog, parent=None, children=None):
        self.runlog = runlog
        self.parent = parent
        if children:
            self.children = children


class RunlogJSONEncoder(JSONEncoder):
    def default(self, obj):

        if not isinstance(obj, RunlogNode):
            return super().default(obj)

        status = obj.runlog["status"]

        if status["type"] == "task_runlog":
            name = status["task_reference"]["name"]
        elif status["type"] == "runbook_runlog":
            if "call_runbook_reference" in status:
                name = status["call_runbook_reference"]["name"]
            else:
                name = status["runbook_reference"]["name"]
        else:
            return "root"

        state = status["state"]

        return "{} (Status: {})".format(name, state)


def watch_action(runlog_uuid, app_name, client, screen=None):
    app = _get_app(client, app_name)
    app_uuid = app["metadata"]["uuid"]

    url = client.application.APP_ITEM.format(app_uuid) + "/app_runlogs/list"
    payload = {"filter": "root_reference=={}".format(runlog_uuid)}

    def poll_func():
        # click.echo("\nPolling action status...")
        return client.application.poll_action_run(url, payload)

    def is_action_complete(response):

        entities = response["entities"]
        if len(entities):

            # Sort entities based on creation time
            sorted_entities = sorted(
                entities, key=lambda x: int(x["metadata"]["creation_time"])
            )

            # Create nodes of runlog tree and a map based on uuid
            root = None
            nodes = {}
            for runlog in sorted_entities:
                # Create root node
                # TODO - Get details of root node
                if not root:
                    root_uuid = runlog["status"]["root_reference"]["uuid"]
                    root_runlog = {
                        "metadata": {"uuid": root_uuid},
                        "status": {"type": "action_runlog", "state": ""},
                    }
                    root = RunlogNode(root_runlog)
                    nodes[str(root_uuid)] = root

                uuid = runlog["metadata"]["uuid"]
                nodes[str(uuid)] = RunlogNode(runlog, parent=root)

            # Attach parent to nodes
            for runlog in sorted_entities:
                uuid = runlog["metadata"]["uuid"]
                parent_uuid = runlog["status"]["parent_reference"]["uuid"]
                node = nodes[str(uuid)]
                node.parent = nodes[str(parent_uuid)]

            # Show Progress
            # TODO - Draw progress bar
            total_tasks = 0
            completed_tasks = 0
            for runlog in sorted_entities:
                runlog_type = runlog["status"]["type"]
                if runlog_type == "task_runlog":
                    total_tasks += 1
                    state = runlog["status"]["state"]
                    if state in RUNLOG.STATUS.SUCCESS:
                        completed_tasks += 1

            if total_tasks:
                screen.clear()
                progress = "{0:.2f}".format(completed_tasks / total_tasks * 100)
                screen.print_at("Progress: {}%".format(progress), 0, 0)

            # Render Tree on next line
            line = 1
            for pre, _, node in RenderTree(root):
                screen.print_at(
                    "{}{}".format(pre, json.dumps(node, cls=RunlogJSONEncoder)), 0, line
                )
                line += 1
            screen.refresh()

            for runlog in sorted_entities:
                state = runlog["status"]["state"]
                if state in RUNLOG.FAILURE_STATES:
                    msg = "Action failed. Exit screen? (y)"
                    screen.print_at(msg, 0, line)
                    screen.refresh()
                    return (True, msg)
                if state not in RUNLOG.TERMINAL_STATES:
                    return (False, "")

            msg = "Action ran successfully. Exit screen? (y)"
            screen.print_at(msg, 0, line)
            screen.refresh()

            return (True, msg)
        return (False, "")

    poll_action(poll_func, is_action_complete)


def watch_app(obj, app_name, action):
    """Watch an app"""

    client = obj.get("client")

    if action:
        return watch_action(action, app_name, client)

    app = _get_app(client, app_name)
    app_id = app["metadata"]["uuid"]
    url = client.application.APP_ITEM.format(app_id) + "/app_runlogs/list"

    payload = {
        "filter": "application_reference=={};(type==action_runlog,type==audit_runlog,type==ngt_runlog,type==clone_action_runlog)".format(
            app_id
        )
    }

    def poll_func():
        click.echo("Polling app status...")
        return client.application.poll_action_run(url, payload)

    def is_complete(response):
        pprint(response)
        if len(response["entities"]):
            for action in response["entities"]:
                state = action["status"]["state"]
                if state in RUNLOG.FAILURE_STATES:
                    return (True, "Action failed")
                if state not in RUNLOG.TERMINAL_STATES:
                    return (False, "")
            return (True, "Action ran successfully")
        return (False, "")

    poll_action(poll_func, is_complete)


def delete_app(obj, app_names, soft):
    client = obj.get("client")

    for app_name in app_names:
        app = _get_app(client, app_name)
        app_id = app["metadata"]["uuid"]
        action_label = "Soft Delete" if soft else "Delete"
        click.echo(">> Triggering {}".format(action_label))
        res, err = client.application.delete(app_id, soft_delete=soft)
        if err:
            raise Exception("[{}] - {}".format(err["code"], err["error"]))

        click.echo("{} action triggered".format(action_label))
        response = res.json()
        runlog_id = response["status"]["runlog_uuid"]
        click.echo("Action runlog uuid: {}".format(runlog_id))


def run_actions(screen, obj, app_name, action_name, watch):
    client = obj.get("client")

    app = _get_app(client, app_name)
    app_spec = app["spec"]
    app_id = app["metadata"]["uuid"]

    calm_action_name = "action_" + action_name.lower()
    action = next(
        action
        for action in app_spec["resources"]["action_list"]
        if action["name"] == calm_action_name or action["name"] == action_name
    )
    if not action:
        raise Exception("No action found matching name {}".format(action_name))
    action_id = action["uuid"]

    # Hit action run api (with metadata and minimal spec: [args, target_kind, target_uuid])
    app.pop("status")
    app["spec"] = {"args": [], "target_kind": "Application", "target_uuid": app_id}
    res, err = client.application.run_action(app_id, action_id, app)

    if err:
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    response = res.json()
    runlog_uuid = response["status"]["runlog_uuid"]
    screen.clear()
    screen.print_at("Got Action Runlog uuid: {}. Fetching runlog tree ...".format(runlog_uuid), 0, 0)
    screen.refresh()
    if watch:
        watch_action(runlog_uuid, app_name, client, screen=screen)


def poll_action(poll_func, completion_func):
    # Poll every 10 seconds on the app status, for 5 mins
    maxWait = 5 * 60
    count = 0
    while count < maxWait:
        # call status api
        res, err = poll_func()
        if err:
            raise Exception("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        (completed, msg) = completion_func(response)
        if completed:
            # click.echo(msg)
            break
        count += 10
        time.sleep(10)
