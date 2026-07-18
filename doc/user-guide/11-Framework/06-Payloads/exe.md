
### Exe Payloads

Single file Python and Shell scripts directly under `lava-payloads` are copied
as is when deployed.

SQL scripts are [Jinja](https://jinja.palletsprojects.com/) rendered at
build/deploy time using the specified environment configuration file, in the
same way as the DynamoDB table specifications.

Jupyter notebooks are converted to Python scripts for deployment.
