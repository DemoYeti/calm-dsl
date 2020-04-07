from calm.dsl.decompile.render import render_template
from calm.dsl.builtins import ProfileType
from calm.dsl.decompile.action import render_action_template
from calm.dsl.decompile.variable import render_variable_template
from calm.dsl.tools import get_logging_handle

LOG = get_logging_handle(__name__)
PROFILE_NAME_MAP = {}


def render_profile_template(cls):

    global PROFILE_NAME_MAP
    LOG.debug("Rendering {} profile template".format(cls.__name__))
    if not isinstance(cls, ProfileType):
        raise TypeError("{} is not of type {}".format(cls, ProfileType))

    # Entity context
    entity_context = "Profile_" + cls.__name__

    user_attrs = cls.get_user_attrs()
    user_attrs["name"] = cls.__name__
    user_attrs["description"] = cls.__doc__ or "{} Profile description".format(
        cls.__name__
    )

    # Update package name map
    gui_display_name = getattr(cls, "name", "")
    if not gui_display_name:
        gui_display_name = cls.__name__

    PROFILE_NAME_MAP[gui_display_name] = cls.__name__

    action_list = []
    for action in user_attrs.get("actions", []):
        action_list.append(render_action_template(action, entity_context))

    deployment_list = []
    for deployment in user_attrs.get("deployments", []):
        deployment_list.append(deployment.__name__)

    variable_list = []
    for entity in user_attrs.get("variables", []):
        variable_list.append(render_variable_template(entity, entity_context))

    user_attrs["variables"] = variable_list
    user_attrs["deployments"] = ", ".join(deployment_list)
    user_attrs["actions"] = action_list

    text = render_template("profile.py.jinja2", obj=user_attrs)
    return text.strip()


def get_profile_display_name(name):
    """returns the class name used for entity ref"""

    global PROFILE_NAME_MAP
    return PROFILE_NAME_MAP.get(name, None)
