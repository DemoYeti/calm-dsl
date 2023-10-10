# THIS FILE IS AUTOMATICALLY GENERATED.
# Disclaimer: Please test this file before using in production.
"""
Generated blueprint DSL (.py)
"""

import json  # no_qa
import os  # no_qa

from calm.dsl.builtins import *  # no_qa
from calm.dsl.constants import PROVIDER

DSL_CONFIG = json.loads(read_local_file(".tests/config.json"))
CENTOS_HM = DSL_CONFIG["AHV"]["IMAGES"]["DISK"]["CENTOS_HADOOP_MASTER"]
PROJECT = DSL_CONFIG["PROJECTS"]["PROJECT1"]
PROJECT_NAME = PROJECT["NAME"]
ENV_NAME = PROJECT["ENVIRONMENTS"][0]["NAME"]

# Credentials
BP_CRED_akhil_cred = basic_cred(
    "root",
    "nutanix/4u",
    name="akhil_cred",
    type="PASSWORD",
    default=True,
)


class Service1(Service):

    service_var = CalmVariable.WithOptions.FromTask(
        CalmTask.Exec.escript.py2(
            name="",
            script='print "akhil"',
        ),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
    )

    @action
    def service_action():

        profile_var = CalmVariable.Simple(
            "",
            label="",
            is_mandatory=False,
            is_hidden=False,
            runtime=False,
            description="",
        )
        CalmTask.Exec.escript.py2(
            name="service_action_task",
            script='print "@@{service_var}@@"',
            target=ref(Service1),
        )


class testvmcalm_random_hashResources(AhvVmResources):

    memory = 1
    vCPUs = 1
    cores_per_vCPU = 1
    disks = [AhvVmDisk.Disk.Scsi.cloneFromImageService(CENTOS_HM, bootable=True)]
    nics = [AhvVmNic.NormalNic.ingress(PROVIDER.AHV.VLAN_1211)]

    guest_customization = AhvVmGC.CloudInit(
        filename="testvmcalm_random_hash_cloud_init_data.yaml"
    )


class testvmcalm_random_hash(AhvVm):

    name = "testvm-@@{calm_random_hash}@@"
    resources = testvmcalm_random_hashResources

    categories = {"AppFamily": "Backup"}


class Service_VM(Substrate):

    account = Ref.Account("NTNX_LOCAL_AZ")
    os_type = "Linux"
    provider_type = "AHV_VM"
    provider_spec = testvmcalm_random_hash
    provider_spec_editables = read_spec("VM1_create_spec_editables.yaml")
    readiness_probe = readiness_probe(
        connection_type="SSH",
        disabled=False,
        retries="5",
        connection_port=22,
        address="@@{platform.status.resources.nic_list[0].ip_endpoint_list[0].ip}@@",
        delay_secs="60",
        credential=ref(BP_CRED_akhil_cred),
    )

    @action
    def __pre_create__():

        CalmTask.Exec.escript.py2(
            name="Python 2 precreate",
            script='print "precreate"',
            target=ref(Service_VM),
        )

    @action
    def post_action_create():

        CalmTask.Exec.escript.py2(
            name="python 2 post create",
            script='print "post create"',
            target=ref(Service_VM),
        )

    @action
    def __post_delete__():

        CalmTask.SetVariable.escript.py2(
            name="python 2 set var",
            script='print "var=postdelete"',
            target=ref(Service_VM),
            variables=["var"],
        )

        CalmTask.Exec.escript.py2(
            name="python 2 post delete",
            script='print "@@{var}@@"',
            target=ref(Service_VM),
        )


class Package1(Package):

    services = [ref(Service1)]

    @action
    def __install__():

        CalmTask.Exec.escript.py2(
            name="python2 package install",
            script='print "package_install"',
            target=ref(Service1),
        )

    @action
    def __uninstall__():

        CalmTask.SetVariable.escript.py2(
            name="python2 package uninstall set var",
            script='print "pack_var=package_unainsta"',
            target=ref(Service1),
            variables=["pack_var"],
        )

        CalmTask.Exec.escript.py2(
            name="python 2 package uninstall read",
            script='print "@@{pack_var}@@"',
            target=ref(Service1),
        )


class _8488e0af_deployment(Deployment):

    name = "8488e0af_deployment"
    min_replicas = "1"
    max_replicas = "1"
    default_replicas = "1"

    packages = [ref(Package1)]
    substrate = ref(Service_VM)


class Default(Profile):

    environments = [Ref.Environment(name=ENV_NAME)]
    deployments = [_8488e0af_deployment]

    profile_level_var = CalmVariable.WithOptions.FromTask(
        CalmTask.Exec.escript.py2(name="", script='print "profile level var"'),
        label="",
        is_mandatory=False,
        is_hidden=False,
        description="",
    )

    @action
    def pythonaction(name="python action"):

        profile_level_action_var = CalmVariable.WithOptions.FromTask(
            CalmTask.Exec.escript.py2(
                name="", script='print "profile_level_action_var"'
            ),
            label="",
            is_mandatory=False,
            is_hidden=False,
            description="",
        )
        with parallel() as p0:
            with branch(p0):
                CalmTask.Exec.escript.py2(
                    name="read_profile_level_var",
                    script='print "@@{profile_level_var}@@"',
                    target=ref(Service1),
                )

                CalmTask.Exec.escript.py2(
                    name="read profile level action var",
                    script='print "@@{profile_level_action_var}@@"',
                    target=ref(Service1),
                )

                Service1.service_action(name="read service action")

                CalmTask.SetVariable.escript.py2(
                    name="set var in profile level",
                    script='print "profile_var=akhil"',
                    target=ref(Service1),
                    variables=["profile_var"],
                )

                CalmTask.Exec.escript.py2(
                    name="read set var in profile level",
                    script='print "@@{profile_var}@@"',
                    target=ref(Service1),
                )


class multi_vm_migrate_blueprint(Blueprint):

    services = [Service1]
    packages = [Package1]
    substrates = [Service_VM]
    profiles = [Default]
    credentials = [BP_CRED_akhil_cred]


class BpMetadata(Metadata):

    project = Ref.Project(PROJECT_NAME)