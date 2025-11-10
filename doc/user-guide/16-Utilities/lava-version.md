
## Lava Version Utility { data-toc-label="lava-version" }

The **lava-version** utility provides version information on the installed lava
version.

??? "Usage"

    ```bare
    usage: lava-version [-h] [-n | -a | --ge VERSION | --eq VERSION]

    Print lava version information.

    optional arguments:
      -h, --help    show this help message and exit
      -n, --name    Print version name only.
      -a, --all     Print all version inforamtion.
      --ge VERSION  Exit with zero status if the lava version is greater than or
                    equal to the specified version.
      --eq VERSION  Exit with zero status if the lava version is equal to the
                    specified version.

    If no arguments are specified the lava version number is printed.
    ```
