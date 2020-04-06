import pytest
import uuid

from calm.dsl.cli.main import get_api_client
from calm.dsl.cli.constants import RUNLOG
from tests.api_interface.test_runbooks.test_files.while_task import WhileTask
from utils import upload_runbook, poll_runlog_status


class TestWhileTasks:
    @pytest.mark.runbook
    @pytest.mark.regression
    def test_while_task_order(self):
        """ test_while_loop_tasks_order """

        client = get_api_client()
        rb_name = "test_whiletask_" + str(uuid.uuid4())[-10:]

        rb = upload_runbook(client, rb_name, WhileTask)
        rb_state = rb["status"]["state"]
        rb_uuid = rb["metadata"]["uuid"]
        print(">> Runbook state: {}".format(rb_state))
        assert rb_state == "ACTIVE"
        assert rb_name == rb["spec"]["name"]
        assert rb_name == rb["metadata"]["name"]

        # endpoints generated by this runbook
        endpoint_list = rb['spec']['resources'].get('endpoint_definition_list', [])

        # running the runbook
        print("\n>>Running the runbook")

        res, err = client.runbook.run(rb_uuid, {})
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))

        response = res.json()
        runlog_uuid = response["status"]["runlog_uuid"]

        # polling till runbook run gets to terminal state
        state, reasons = poll_runlog_status(client, runlog_uuid, RUNLOG.TERMINAL_STATES, maxWait=480)

        print(">> Runbook Run state: {}\n{}".format(state, reasons))
        assert state == RUNLOG.STATUS.SUCCESS

        # Check order of tasks execution inside while loop
        timestamps = dict()
        res, err = client.runbook.list_runlogs(runlog_uuid)
        res, err = client.runbook.list_runlogs(runlog_uuid)
        if err:
            pytest.fail("[{}] - {}".format(err["code"], err["error"]))
        response = res.json()
        entities = response["entities"]
        for entity in entities:
            if entity["status"]["type"] == "task_runlog":
                task_name = entity["status"]["task_reference"]["name"]
                machine_name = entity["status"].get("machine_name", "")
                if len(machine_name.split(runlog_uuid)) == 2 or not entity["status"].get("loop_counter", None):
                    continue
                if int(entity["status"]["loop_counter"]) > 0:
                    pytest.fail("Executed {} iteration of {}".format(int(entity["status"]["loop_counter"]) + 1, task_name))
                timestamps[task_name] = dict()
                timestamps[task_name]["start"] = entity["metadata"]["creation_time"]
                timestamps[task_name]["end"] = entity["metadata"]["last_update_time"]

        for index in range(1, 14):
            task_name = "Task" + str(index)
            next_task = "Task" + str(index + 1)
            assert timestamps[task_name]["end"] <= timestamps[next_task]["start"]

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
