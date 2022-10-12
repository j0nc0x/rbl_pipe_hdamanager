name = "rbl_pipe_hdamanager"

version = "1.2.0"

authors = [
    "Jonathan Cox",
]

requires = [
        "houdini",
        "rbl_pipe_python_extras-1.4+<2",
        "rbl_pipe_core-0.11+<1",
        "rbl_pipe_houdini-2",
        ]

release_target = "int"

def commands():
    # Have to use set to prepend rather than prepend, as otherwise the PYTHONPATH set by shotgun will be overwritten
    env.PYTHONPATH.set("{root}/rbl_pipe_hdamanager/lib/python:$PYTHONPATH")
    env.HOUDINI_MENU_PATH.prepend("{root}/rbl_pipe_hdamanager/dcc/houdini/menu")
