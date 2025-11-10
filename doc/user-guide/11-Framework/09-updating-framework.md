
## Updating the Framework in an Existing Project { data-toc-label="Updating the Framework" }

The lava framework can be updated for an existing project by obtaining the new
framework package `cookiecutter-lava-<NEW-VERSION>.zip` and applying it over the
top of the project.

This process is automated by the framework itself. A backup is made first as
part of the process in case of problems. However it is strongly recommended to
do a `git commit` and `git push` before starting the process.

The update process is relatively straightforward when updating from a framework
version of 5.1.0 (Tungurahua) or above. Updating earlier versions is possible
with a little bit of fiddling.

#### Updating from Lava Version 5.1.0 (Tungurahua) or Above

The process is:

```bash
# Go to the project root directory. Then ...
# Commit and push your code just in case. Then ...
# Deposit the new package at the root of the project directory. Then ...

# Activate the virtual environment
source venv/bin/activate

# Run the update process
make update pkg=cookiecutter-lava-<NEW-VERSION>.zip
```

This will do a backup of the project into a zip file, rerun the cookiecutter
using the new package and apply the new framework components over the existing
project.

#### Updating from Lava Versions Prior to 5.1.0 (Tungurahua)

The process is:

```bash
# Go to the project root directory. Then ...
# Commit and push your code just in case. Then ...
# Deposit the new package at the root of the project directory. Then ...

# Extract the `bin` directory from the new framework package
# The quotes are important here.
unzip -j -d bin cookiecutter-lava-<NEW-VERSION>.zip '*bin/*'
chmod u+x bin/*

# Activate the virtual environment
source venv/bin/activate

# Run the update process
PATH=$(pwd)/bin:$PATH make update pkg=cookiecutter-lava-<NEW-VERSION>.zip
```

Note that later versions of the framework move the framework's
`requirements.txt` file into the `etc` directory. After the update the
`requirements.txt` in the base directory can be deleted if there are no locally
added packages. If there are, only those packages need to be retained in that file.
