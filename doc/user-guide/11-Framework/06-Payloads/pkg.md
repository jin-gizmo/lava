
### Pkg Payloads

Directories directly under `lava-payloads` with names ending in `.pkg` are
assumed to contain the code for lava [pkg](#job-type-pkg) jobs.

The build process is essentially:

1.  Create a clean copy of the source tree.

2.  Any files in the `env/` directory of the source tree are Jinja rendered
    using the environment configuration file. This provides one possible
    mechanism to include environment specific information in the build.

3.  Any Jupyter notebooks (`*.ipynb`) are converted to Python.

4.  If the root directory of the source tree contains a
    `requirements.txt` file, then Python modules listed therein, including any
    dependencies, are included.

5.  If the root directory contains a `requirements-nodeps.txt` file, then Python
    modules listed therein, excluding any dependencies, are included.
    
6.  Zip up everything and place it in the `dist` area of the project.

