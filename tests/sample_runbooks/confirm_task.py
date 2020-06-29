"""
Calm DSL Confirm Task Example

"""

from calm.dsl.builtins import runbook
from calm.dsl.builtins import CalmTask as Task


code = '''print "Hello"
print "Bye"'''


@runbook
def DslConfirmRunbook():
    "Runbook Service example"
    Task.Confirm(name="Confirm_Task")
    Task.Exec.escript(name="Exec_Task", script=code)


def main():
    print(DslConfirmRunbook.runbook.json_dumps(pprint=True))


if __name__ == "__main__":
    main()
