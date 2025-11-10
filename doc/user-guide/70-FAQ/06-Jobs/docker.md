
### docker

#### You must specify a region

If a [docker](#job-type-docker) job requires access to AWS
resources (e.g. S3, the lava connections manager etc.) it will be using the
boto3 Python module to do so. This requires the AWS region in which it runs to
be specified. Rather than hard-wire that into the container, the easiest way to
set this is by adding the following environment variable to the parameters in
the job specification:

```json
{
    "parameters": {
        "env": {
         "AWS_DEFAULT_REGION": "ap-southeast-2"
        }
    }
}
```

Note that the IAM role for the worker should provide the authentication
requirements for docker containers running on that worker.
