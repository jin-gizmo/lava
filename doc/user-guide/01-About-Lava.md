
# About Lava

!!! warning ""
    **Lava** was developed at [Origin Energy](https://www.originenergy.com.au) as part of the
    *Jindabyne* initiative. While not part of our core IP, it proved valuable
    internally, and we're sharing it in the hope it's useful to others.

    [![Jin Gizmo Home](https://img.shields.io/badge/Jin_Gizmo_Home-d30000?logo=GitHub&color=d30000)](https://jin-gizmo.github.io)

    Kudos to Origin for fostering a culture that empowers its people
    to build complex technology solutions in-house.

<div style="text-align: center;">
  <img src="img/lava-icons/svg/256/lava-icon-256-transparent.svg" 
       alt="Lava Logo" 
       width="150" 
       height="auto"
       class="lava-logo">
</div>

**Lava** is an AWS based distributed scheduler and job runner. It is scalable,
robust and built using native AWS components, wherever possible.

Lava has been used extensively in a large, business critical data warehouse /
data lake environment to run tens of thousands of jobs a day on a 24x7 basis,
with jobs lasting anywhere between a few seconds and 12 hours.


Typical jobs perform tasks such as:

*   AWS environment command and control

*   Data ETL jobs, large and small

*   Inter-company data exchanges.

Lava was built as a result of terminal frustration with some commercial and open
source options. Too often, these proved to be hard to install, maintain or use
in a complex multi-user, multi-environment context.

## Features

**Lava** features include:

*   Provision of an integrated orchestration and execution environment that is
    readily scalable from a desktop installation to a large auto scaling fleet.

*   Jobs can be scheduled, triggered by AWS and external events, or initiated by
    other jobs.

*   Ability to connect to a variety of database types, including Postgres, MySQL,
    Oracle, Microsoft SQL Server and Redshift.

*   Enhanced support for some AWS RDS and RDS Aurora databases.

*   Built-in connectors to a handful of useful services, including databases,
    file shares, Microsoft SharePoint, email servers and Slack.

*   Ability to run SQL jobs as well as executable payloads, including docker
    based payloads and native code bundles.

*   Secure management of connection credentials to avoid the need to embed them
    into job payloads.

## Design Principles

Lava is based on the following principles:

*   Most people want to do simple tasks so make doing these as simply as
    scalability and robustness requirements allow.

*   It should be quick and simple to deploy.

*   AWS native components should be used wherever possible, instead of
    installing specialised software components.

*   Existing, tried and tested standard Linux operating system components
    should be used wherever possible.

*   Simple, robust, transparent operation.

*   Scalable and reliable.

*   Simple, visible configuration.

*   Jobs are trusted within their operating environment.

These principles led to the following design decisions:

*   All configuration information is stored in AWS DynamoDB.

*   Job payloads are stored in AWS S3 or AWS ECR and job outputs are stored in
    S3.

*   Execution workers are completely stateless and powered by a single Python
  based code bundle that can be installed on a standard Linux instance at
  boot time or run in a docker container.

*   Linux **cron** is used for dispatching scheduled jobs.

*   Event driven jobs can be dispatched by AWS facilities such as S3 bucket event
    notifications and Amazon EventBridge.

*   AWS SQS is used to dispatch jobs to workers.

*   Logging uses AWS CloudWatch (logs and metrics), DynamoDB and S3.

*   AWS IAM and KMS are used to manage much of the security.

*   AWS SSM Parameter Store and/or AWS Secrets Manager are used to store job
    specific parameters. Encrypted parameters store sensitive ones.
    
*   Deployment of a lava environment and worker instances is done using
    supplied CloudFormation templates.
    
*   AWS ECR is supported for docker related aspects of lava.

*   Lava worker nodes can use AWS EC2 auto scaling groups for robustness.
    The supplied CloudFormation templates will set these up.
    
*   Jobs can use SQS, SES and SNS (among other things) to send messages to
    external components.

*   AWS Lambda is used for some support functions.

## Authors

Murray Andrews, Chris Donoghue and Alex Boul.
