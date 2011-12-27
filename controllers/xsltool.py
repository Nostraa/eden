# -*- coding: utf-8 -*-

"""
    XSL Tool
"""

module = request.controller
resourcename = request.function

if module not in deployment_settings.modules:
    raise HTTP(404, body="Module disabled: %s" % module)

# Load Models


# Options Menu (available in all Functions' Views)
s3_menu(module)


# S3 framework functions
# -----------------------------------------------------------------------------
def index():

    """ Module's Home Page """
    module_name = deployment_settings.modules[module].name_nice
    response.title = module_name
    return dict(module_name=module_name)
