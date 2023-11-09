# THIS FILE IS AUTOMATICALLY GENERATED.
# Disclaimer: Please test this file before using in production.
"""
Generated environment DSL (.py)
"""

from calm.dsl.builtins import *

# Secret Variables
BP_CRED_test_cred_PASSWORD = read_local_file("BP_CRED_test_cred_PASSWORD")
BP_CRED_test_cred = basic_cred(
    "admin",
    BP_CRED_test_cred_PASSWORD,
    name="test_cred",
    type="PASSWORD",
)


class Untitled(Substrate):

    os_type = "Linux"
    provider_type = "GCP_VM"
    provider_spec = read_provider_spec(
        os.path.join("specs", "Untitled_provider_spec.yaml")
    )

    readiness_probe = readiness_probe(
        connection_type="SSH",
        disabled=True,
        retries="5",
        connection_port=22,
        address="@@{platform.networkInterfaces[0].accessConfigs[0].natIP}@@",
        delay_secs="60",
    )


class Untitled_1(Substrate):

    name = "Untitled"

    os_type = "Windows"
    provider_type = "GCP_VM"
    provider_spec = read_provider_spec(
        os.path.join("specs", "Untitled_1_provider_spec.yaml")
    )

    readiness_probe = readiness_probe(
        connection_type="POWERSHELL",
        disabled=True,
        retries="5",
        connection_port=5985,
        address="@@{platform.networkInterfaces[0].accessConfigs[0].natIP}@@",
        delay_secs="60",
    )


class ENV_test_decompile_env_gcp(Environment):
    substrates = [Untitled, Untitled_1]
    credentials = [BP_CRED_test_cred]

    providers = [
        Provider.Gcp(
            account=Ref.Account("GCP"),
        ),
    ]
