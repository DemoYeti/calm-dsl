from calm.dsl.decompile.render import render_template
from calm.dsl.decompile.task import render_task_template

from calm.dsl.log import get_logging_handle

LOG = get_logging_handle(__name__)


def render_task_tree_template(
    root_node,
    task_child_map,
    entity_context,
    RUNBOOK_ACTION_MAP,
    CONFIG_SPEC_MAP,
    context="",
    secrets_dict=[],
):
    """render task tree template"""

    rendered_tasks = {}
    for task_key in task_child_map:
        for task in task_child_map[task_key]:
            rendered_tasks[task.get("task_name")] = render_task_template(
                task.get("task_data"),
                entity_context,
                RUNBOOK_ACTION_MAP,
                CONFIG_SPEC_MAP,
                context=context,
                secrets_dict=secrets_dict,
            )

    task_indent_tree = []
    visited = []

    def generate_task_tree(
        task_child_map, visited, current_task, parent_task, depth, parent_indent
    ):
        """
        generates the information required to indent tasks correctly

        Args:
            task_child_map (dict) : stores info about (task_name, depth) and its child tasks.
            visited ([str]) : array of tasks that have been visited during this dfs.
            current_task (str) : the current task being processed.
            parent_task (str) : parent task of current task.
            depth (int) : depth of the task in the tree.
            parent_indent (int) : indent of the parent task.
        """
        current_indent = parent_indent

        # if the current node has more than one children only then we require a helper `with parallel() / with branch()`
        is_branch_required = len(task_child_map[(parent_task, max(0, depth - 1))]) > 1
        # if we have not visited parent task
        if parent_task not in visited:
            if current_task != root_node:
                visited.append(parent_task)
                # if the task requires a helper, then we add indentation for the parallel helper, branch helper, task
                # `with parallel()` would have the same indent as parent_task and `with branch()` would have its indentaion parallel_indent+1
                # task's indent would be branch_indent+1, hence parallel_indent+2
                if is_branch_required:
                    current_indent = parent_indent + 2
                    task_indent_tree.append(
                        {
                            "parallel_indent": parent_indent,
                            "branch_indent": parent_indent + 1,
                            "task_indent": current_indent,
                            "task": current_task,
                            "depth": depth,
                        }
                    )
                else:
                    # if parent task is root_node(the one which we assigned the name with a random uuid) then tere is no need for any helper(parallel / branch)
                    task_indent_tree.append(
                        {
                            "parallel_indent": None,
                            "branch_indent": None,
                            "task_indent": current_indent,
                            "task": current_task,
                            "depth": depth,
                        }
                    )
        else:
            # if the parent has been visited then the child would not have a `with parallel()`
            # the child will either be present as an individual task or `with branch()` helper would be used
            # so, in both below cases - parallel_indent is set as None

            # if is_branch_required is true then we require `with branch()` helper and we set its indentation as required
            if is_branch_required:
                current_indent = parent_indent + 2
                task_indent_tree.append(
                    {
                        "parallel_indent": None,
                        "branch_indent": parent_indent + 1,
                        "task_indent": current_indent,
                        "task": current_task,
                        "depth": depth,
                    }
                )
            # the task doesn't require any helper so branch_indent is set as None
            else:
                task_indent_tree.append(
                    {
                        "parallel_indent": None,
                        "branch_indent": None,
                        "task_indent": current_indent,
                        "task": current_task,
                        "depth": depth,
                    }
                )

        task_key = (current_task, depth)
        if task_key in task_child_map:
            # Iterating through all the children of current task
            for child_task in task_child_map[task_key]:
                # calling generate_task_tree recursively for each child task
                generate_task_tree(
                    task_child_map,
                    visited,
                    child_task["task_name"],
                    current_task,
                    depth + 1,
                    current_indent,
                )

    generate_task_tree(task_child_map, visited, root_node, root_node, 0, 0)

    user_attrs = {
        "tasks": rendered_tasks,
        "task_indent_tree": task_indent_tree,
    }

    text = render_template(schema_file="task_tree.py.jinja2", obj=user_attrs)
    return text.strip()
