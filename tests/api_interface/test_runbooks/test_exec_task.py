import pytest
import uuid

from calm.dsl.cli.main import get_api_client
from calm.dsl.cli.constants import RUNLOG
from calm.dsl.config import get_context
from tests.api_interface.test_runbooks.test_files.exec_task import (
    EscriptTask,
    EscriptMacroTask,
    SetVariableOnEscript,
    EscriptOnEndpoint,
    PowershellTask,
    SetVariableOnPowershell,
    PowershellOnMultipleIPs,
    PowershellWithCredOverwrite,
    ShellTask,
    SetVariableOnShell,
    ShellOnMultipleIPs,
    ShellWithCredOverwrite,
    PowershellTaskWithoutTarget,
    ShellTaskWithoutTarget,
    MacroOnShell,
    MacroOnPowershell,
    MacroOnEscript,
    EndpointMacroOnShell,
    EndpointMacroOnPowershell,
    LinuxEndpointMacroOnEscript,
    WindowsEndpointMacroOnEscript,
    HttpEndpointMacroOnEscript,
)
from utils import upload_runbook, poll_runlog_status

# TODO: Add validation for macro test values: EscriptMacroTask
class TestExecTasks:
    @pytest.mark.escript
    @pytest.mark.runbook
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "Runbook",
        [
            EscriptTask,
            EscriptMacroTask,
            SetVariableOnEscript,
            EscriptOnEndpoint,
            PowershellTask,
            SetVariableOnPowershell,
            PowershellWithCredOverwrite,
            ShellTask,
            SetVariableOnShell,
            ShellWithCredOverwrite,
            ShellOnMultipleIPs,
            PowershellOnMultipleIPs,
        ],
    )
    def test_script_run(self, Runbook):
        """test_access_set_variable_in_next_task, test_escript_task,
        test_script_type_escript_execute_task_on_endpoint_with_multiple_ips,
        test_rb_run_with_script_type_powershell_setVariable_task,
        test__script_type_powershell_execute_task,
        test_powershell_on_default_target,
        test_script_type_powershell_execute_task_on_endpoint_with_multiple_ips,
        test_script_credential_overwrite for powershell task,
        test_rb_run_with_script_type_shell_setVariable_task,
        test_script_type_shell_execute_task,
        test_shell_on_default_target,
        test_script_credential_overwrite for shell task"""

        client = get_api_client()
        rb_name = "test_exectask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, Runbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # endpoints generated by this runbook
        endpoint_list = rb["spec"]["resources"].get("endpoint_definition_list", [])

        # running the runbook
        print("\n>>Running the runbook")

        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(
            client, runlog_uuid, RUNLOG.TERMINAL_STATES, maxWait=360
        )

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # Finding the trl id for the exec task (all runlogs for multiple IPs)
        exec_tasks = []
        res, err = client.runbook.list_runlogs(runlog_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        entities = response["entities"]
        for entity in entities:
            if (
                entity["status"]["type"] == "task_runlog"
                and entity["status"]["task_reference"]["name"] == "ExecTask"
                and runlog_uuid in entity["status"].get("machine_name", "")
            ):
                exec_tasks.append(entity["metadata"]["uuid"])

        # Now checking the output of exec task
        for exec_task in exec_tasks:
            res, err = client.runbook.runlog_output(runlog_uuid, exec_task)
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
            runlog_output = res.json()
            output_list = runlog_output["status"]["output_list"]
            assert "Task is Successful" in output_list[0]["output"]

        # delete the runbook
        _, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            print("runbook {} deleted".format(rb_name))

        # delete endpoints generated by this test
        for endpoint in endpoint_list:
            _, err = client.endpoint.delete(endpoint["uuid"])
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))

    @pytest.mark.escript
    @pytest.mark.runbook
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "Runbook", [PowershellTaskWithoutTarget, ShellTaskWithoutTarget]
    )
    def test_exec_validations(self, Runbook):
        """
        test_powershell_without_target, test_shell_on_default_target
        """
        client = get_api_client()
        rb_name = "test_exectask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, Runbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "DRAFT"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # checking validation errors
        task_list = rb["status"]["resources"]["runbook"]["task_definition_list"]
        for task in task_list:
            if task["type"] == "ExecTask":
                validation_errors = ""
                for message in task["message_list"]:
                    validation_errors += message["message"]
                assert (
                    "No default endpoint or endpoint at task level."
                    in validation_errors
                )

        # delete the runbook
        _, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            print("runbook {} deleted".format(rb_name))

    @pytest.mark.escript
    @pytest.mark.runbook
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "Runbook", [MacroOnShell, MacroOnPowershell, MacroOnEscript]
    )
    def test_macro_in_script(self, Runbook):
        """test_macro_in_script"""

        client = get_api_client()
        rb_name = "test_exectask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, Runbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # endpoints generated by this runbook
        endpoint_list = rb["spec"]["resources"].get("endpoint_definition_list", [])

        # running the runbook
        print("\n>>Running the runbook")

        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(
            client, runlog_uuid, RUNLOG.TERMINAL_STATES, maxWait=360
        )

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # Finding the trl id for the exec task (all runlogs for multiple IPs)
        exec_tasks = []
        res, err = client.runbook.list_runlogs(runlog_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        entities = response["entities"]
        for entity in entities:
            if (
                entity["status"]["type"] == "task_runlog"
                and entity["status"]["task_reference"]["name"] == "ExecTask"
            ):
                exec_tasks.append(entity["metadata"]["uuid"])

        ContextObj = get_context()
        project_config = ContextObj.get_project_config()
        project_name = project_config["name"]

        # Now checking the output of exec task
        for exec_task in exec_tasks:
            res, err = client.runbook.runlog_output(runlog_uuid, exec_task)
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
            runlog_output = res.json()
            output_list = runlog_output["status"]["output_list"]
            assert rb_name in output_list[0]["output"]
            assert rb_uuid in output_list[0]["output"]
            assert project_name in output_list[0]["output"]

        # delete the runbook
        _, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            print("runbook {} deleted".format(rb_name))

        # delete endpoints generated by this test
        for endpoint in endpoint_list:
            _, err = client.endpoint.delete(endpoint["uuid"])
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))

    @pytest.mark.escript
    @pytest.mark.runbook
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "Runbook",
        [
            EndpointMacroOnShell,
            EndpointMacroOnPowershell,
            LinuxEndpointMacroOnEscript,
            WindowsEndpointMacroOnEscript,
        ],
    )
    def test_os_endpoint_macro_in_script(self, Runbook):
        """test_macro_in_script"""

        client = get_api_client()
        rb_name = "test_exectask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, Runbook)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # endpoints generated by this runbook
        endpoint_list = rb["spec"]["resources"].get("endpoint_definition_list", [])

        endpoint_uuid_used = (
            rb["spec"]["resources"].get("default_target_reference", {}).get("uuid", "")
        )
        for task in rb["spec"]["resources"]["runbook"].get("task_definition_list", []):
            if task["name"] == "ExecTask" and task.get(
                "target_any_local_reference", {}
            ).get("uuid", ""):
                endpoint_uuid_used = task.get("target_any_local_reference", {}).get(
                    "uuid", ""
                )

        assert endpoint_uuid_used

        endpoint_used = None
        for endpoint in endpoint_list:
            if endpoint["uuid"] == endpoint_uuid_used:
                endpoint_used = endpoint

        # running the runbook
        print("\n>>Running the runbook")

        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(
            client, runlog_uuid, RUNLOG.TERMINAL_STATES, maxWait=360
        )

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # Finding the trl id for the exec task (all runlogs for multiple IPs)
        exec_tasks = []
        res, err = client.runbook.list_runlogs(runlog_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        entities = response["entities"]
        for entity in entities:
            if (
                entity["status"]["type"] == "task_runlog"
                and entity["status"]["task_reference"]["name"] == "ExecTask"
                and runlog_uuid in entity["status"].get("machine_name", "")
            ):
                exec_tasks.append(entity["metadata"]["uuid"])

        # Now checking the output of exec task
        for exec_task in exec_tasks:
            res, err = client.runbook.runlog_output(runlog_uuid, exec_task)
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
            runlog_output = res.json()
            output_list = runlog_output["status"]["output_list"]

            assert endpoint_used["name"] in output_list[0]["output"]
            assert endpoint_used["type"] in output_list[0]["output"]
            address_in_output = False
            for address in endpoint_used["attrs"]["values"]:
                if address in output_list[0]["output"]:
                    address_in_output = True

            assert address_in_output
            assert str(endpoint_used["attrs"]["port"]) in output_list[0]["output"]
            cred_username = endpoint_used["attrs"]["credential_definition_list"][0][
                "username"
            ]
            assert cred_username in output_list[0]["output"]

            if endpoint_used["type"] == "Windows":
                assert (
                    endpoint_used["attrs"]["connection_protocol"]
                    in output_list[0]["output"]
                )

        # delete the runbook
        _, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            print("runbook {} deleted".format(rb_name))

        # delete endpoints generated by this test
        for endpoint in endpoint_list:
            _, err = client.endpoint.delete(endpoint["uuid"])
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))

    @pytest.mark.runbook
    @pytest.mark.regression
    def test_http_endpoint_macro_in_script(self):
        """test_macro_in_script"""

        client = get_api_client()
        rb_name = "test_exectask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, HttpEndpointMacroOnEscript)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # endpoints generated by this runbook
        endpoint_list = rb["spec"]["resources"].get("endpoint_definition_list", [])

        endpoint_uuid_used = (
            rb["spec"]["resources"].get("default_target_reference", {}).get("uuid", "")
        )
        for task in rb["spec"]["resources"]["runbook"].get("task_definition_list", []):
            if task["name"] == "ExecTask" and task.get(
                "target_any_local_reference", {}
            ).get("uuid", ""):
                endpoint_uuid_used = task.get("target_any_local_reference", {}).get(
                    "uuid", ""
                )

        assert endpoint_uuid_used

        endpoint_used = None
        for endpoint in endpoint_list:
            if endpoint["uuid"] == endpoint_uuid_used:
                endpoint_used = endpoint

        # running the runbook
        print("\n>>Running the runbook")

        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(
            client, runlog_uuid, RUNLOG.TERMINAL_STATES, maxWait=360
        )

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # Finding the trl id for the exec task (all runlogs for multiple IPs)
        exec_tasks = []
        res, err = client.runbook.list_runlogs(runlog_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        entities = response["entities"]
        for entity in entities:
            if (
                entity["status"]["type"] == "task_runlog"
                and entity["status"]["task_reference"]["name"] == "ExecTask"
                and runlog_uuid in entity["status"].get("machine_name", "")
            ):
                exec_tasks.append(entity["metadata"]["uuid"])

        # Now checking the output of exec task
        for exec_task in exec_tasks:
            res, err = client.runbook.runlog_output(runlog_uuid, exec_task)
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
            runlog_output = res.json()
            output_list = runlog_output["status"]["output_list"]

            assert endpoint_used["name"] in output_list[0]["output"]
            assert endpoint_used["type"] in output_list[0]["output"]
            base_url_in_output = False
            for base_url in endpoint_used["attrs"]["urls"]:
                if base_url in output_list[0]["output"]:
                    base_url_in_output = True

            assert base_url_in_output
            assert (
                str(endpoint_used["attrs"]["tls_verify"]).upper()
                in (output_list[0]["output"]).upper()
            )
            assert (
                str(endpoint_used["attrs"]["retry_interval"])
                in output_list[0]["output"]
            )
            assert (
                str(endpoint_used["attrs"]["retry_count"]) in output_list[0]["output"]
            )
            assert (
                str(endpoint_used["attrs"]["connection_timeout"])
                in output_list[0]["output"]
            )

        # delete the runbook
        _, err = client.runbook.delete(rb_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        else:
            print("runbook {} deleted".format(rb_name))

        # delete endpoints generated by this test
        for endpoint in endpoint_list:
            _, err = client.endpoint.delete(endpoint["uuid"])
            if err:
                pytest.fail("[{}] - {}".format(err["code"], err["error"]))
