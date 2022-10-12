# Introduction
HDAs are an essential building block of any pipeline that makes use of Houdini. They allow for tools, workflows and setups to be wrapped up into a single node, with a basic interface, that can be reused in multiple scenes by multiple artists. 

Some examples might be:
- A farm submitter HDA: A pipeline tool that wraps up a collection of nodes / code that allows a scene to be submitted to the farm.
- A FX ocean HDA: An FX artist tool that wraps up an ocean FX setup with some common settings that can be used to control it across multiple shots.

As shown by the above examples, HDAs can be really useful both as tools constructed by the Pipeline team to allow certain tasks to be completed, but also to artists / leads who want to wrap up setups into a resusable node with a simplified interface. An added benefit from the artis side, is that setups created in Houdini FX, which make use of DOPs simulations can be wrapped into HDAs and used in Houdini Core, meaning a lead can work on a simulation and wrap it up into a simple HDA with a few basic controls that a junior artist can use to control it.

It is also really important to version and track the HDAs used within the Houdini environment, as changes to a HDA will propogate into a scene file, meaning it is really easy to break many scene files with just one change.

The above points mean that it is really important to have an easy to use and robust story with regard to HDA management, and that it is especially important to make it easily available and accessible to artists. This is the main rational behind the creation of the Rebellion HDA Manager.

# HDA Management Basics
Houdini allows HDAs to be loaded into the environment in two main ways:
- Appending directories containing HDAs to the `HOUDINI_OTLSCAN_PATH`. These HDAs will then be loaded by Houdini when it starts.
- Installing and uninstalling HDAs where needed using the API.

Using the `HOUDINI_OTLSCAN_PATH` is a very basic way of managing HDAs in the Houdini environment, and doesn't offer much flexibility. Using the Houdini API to control which HDAs are available within the Houdini environment involves a little more work, but offers a lot finer control and lends itself well to being used as the mechanism behind a HDA "Manager". This is the approach we took with the Rebellion HDA Manager.

# HDA Packages
The HDA Manager is designed around the concept of "HDA Packages". These are collections of HDAs that are grouped together into a rez package to make it easier to deploy them. For example, we have HDA Packages for pipeline (`houdini_hdas_pipeline`) and also for the global artist-created HDAs (`houdini_hdas_global`).

The HDA Manager loads these packages by looking for the `REBELLION_HDAS` environment variable, which each HDA package appends it's root directory to.

In addition to these HDA packages a separate HDA package is automatically added by the HDA manager to handle the HDAs that are currently being edited by the HDA manager - ie. the HDAs that reside in `$HOUDINI_USER_PREF_DIR/otls/hdamanager`.

# Loading HDAs
When the HDA Manager is started (ie. a new instance of `HDAManager` is created), the rough process of HDAs being loaded is:
- `HDAManager.initialise_repositories` creates a `HDARepo` instance for each HDA package found in the `REBELLION_HDAS` environment variable as well as for the local `editable` HDA package.
- `HDAManager.load_all` calls `HDARepo.load` for each HDA Repo that was created in the previous step.
- For each Houdini Node Type found, a `NodeType` instance is created. A `NodeTypeVersion` instance is created for the specific version of the Node Type being loaded.
- `NodeTypeVersion.install_definition` calls `hou.hda.installFile` to install the HDA and make it available within the Houdini session.

# HDA Versions
Houdini HDAs using namespaced Node Type Names allows for multiple versions of the same HDA. These multiple versions can be separated by namespace or by version.

Taking the HDA `amazinghda` as an example:
- `rebellion.pipeline::amazinghda::1.0.0` and `rebellion.global::amazinghda::1.0.0` define two versions of the same Node Type that have different namespaces.
- `rebellion.pipeline::amazinghda::1.0.0` and `rebellion.pipeline::amazinghda::1.1.0` define two versions of the same Noe Type that have differen version numbers.

In the HDA manager we map Node Type namespaces to HDA packages, so `rebellion.pipeline` maps to `houdini_hdas_pipeline` for example.

Versions are handled differently. The HDA manager scans multiple versions of the HDA package, starting with the current version and counting backwards. By default this scanning process is limited to the HDA package major version. The number of versions installed per Node Type is controlled by the `HDA_MANAGER_LOAD_DEPTH` environment variable to avoid having too many versions loaded at once.

# Editing HDAs
When a user wants to make edits to a HDA the HDA Manager makes a copy of the HDA file in `$HOUDINI_USER_PREF_DIR/otls/hdamanager` and it gets added to the `editable` `HDARepo`.