# Dockerfile to set up a basic Microsoft SQL Server DB.

# The standard Microsoft image doesn't work on M-series ARM but we can use the
# Azure Edge image which is close enough. However, this image doesn't include
# the SQL tools (sqlcmd) which we need to be able to initialise the database
# so we add that here.

# See: https://learn.microsoft.com/en-au/sql/tools/sqlcmd/sqlcmd-utility?view=sql-server-ver16&tabs=go%2Clinux&pivots=cs1-bash#download-and-install-sqlcmd

# WARNING:  At the time of writing, the Microsoft image uses Ubuntu 18.04 but
#           the open source sqlcmd is provided (by Microsoft) for Ubuntu 20.04.
#           So, we have to wing it and install the 20.04 sqlcmd on 18.04.
#           _Please_ don't tell me that Microsoft now gets Linux.

FROM mcr.microsoft.com/azure-sql-edge:latest

USER root
RUN \
    apt-get update ; \
    curl https://packages.microsoft.com/keys/microsoft.asc > /etc/apt/trusted.gpg.d/microsoft.asc ; \
    apt-get install software-properties-common -y ; \
    add-apt-repository "$(wget -qO- https://packages.microsoft.com/config/ubuntu/20.04/prod.list)" ; \
    apt-get install gettext sqlcmd -y ; \
    :

# USER mssql
