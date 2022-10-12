cmake_minimum_required(VERSION 2.8)

include(RezBuild)

file(GLOB_RECURSE py_files "lib/python/*.py")
rez_install_files(
    ${py_files}
    DESTINATION rbl_pipe_hdamanager
)

file(GLOB_RECURSE menu_files "dcc/houdini/*")
rez_install_files(
    ${menu_files}
    DESTINATION rbl_pipe_hdamanager
)

file(GLOB_RECURSE config "config/*")
rez_install_files(
    ${config}
    DESTINATION rbl_pipe_hdamanager
)
