# -*- coding: utf-8 -*-

"""
    CAP-Broker
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

def add():
    response.title = T("Create a new CAP notification")
    return dict()

def add_profiles():
    response.title = T("Create a new CAP profile")
    return dict()

def edit_profiles():
    response.title = T("Edit CAP default values and profiles")
    return dict()

def edit_lang_template():
    response.title = T("Edit CAP default values and profiles")
    return dict()

def edit_msg_info():
    response.title = T("Edit CAP message info")
    return dict()

def edit_area():
    response.title = T("Edit CAP message area")
    return dict()

def issue():
    response.title = T("Issue CAP message")
    return dict()
