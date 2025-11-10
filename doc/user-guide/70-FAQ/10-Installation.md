
## Installation and Operation FAQ

### The Lava Worker

#### ModuleNotFoundError: No module named 'psutil'

This error appears to be unique to the Amazon Linux 1 AMI due to a bug in the
Python configuration on that AMI. Basically, binary modules, such as `psutil`,
are getting installed in a `lib64` directory by pip instead of `lib` and Python
is not looking in `lib64`.

The fix is:

```bash
unset PYTHON_INSTALL_LAYOUT
python3 -m pip install psutil --upgrade
```
Note that this problem can also affect other modules including `jinja2` and
`cx_Oracle`. The fix is the same in each case.

### The Lava Docker Images

#### Docker build fails : ERROR [internal] load metadata for docker.io...

There is a bug in some versions of docker buildkit which seems to occur when
connecting to docker hub via a proxy. If this message occurs, try building from
location that does not require a proxy connection.

!!! info
    As of v8.1.0 ([Kīlauea](https://en.wikipedia.org/wiki/Kīlauea)), lava docker
    images _must_ be built with buildkit enabled.
