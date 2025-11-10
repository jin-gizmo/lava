
# The Lava State Manager { x-nav="Lava State Manager" }

Lava jobs generally act in isolation from each other or within the scope of a
controlling master job that can pass global variables to the child jobs. In
some situations, it is useful for one job to be able to pass state information
directly to other jobs in a peer to peer fashion.

The **lava state manager** provides the ability for a job to publish state
information (state items) for subsequent use by another job or by an authorised
external entity. **State items** are persistent, structured data elements with a
defined expiry time. State items are stored in the [state](#the-state-table)
DynamoDB table.

!!! note
    The state manager is intended for use with small amounts of data (e.g.
    control parameters, job status information etc.). Where large amounts of
    data need to be exchanged between jobs, S3 is the preferred solution.

The state manager supports the following capabilities:

*   Ability to [post state items](#posting-state-items) from lava jobs and
    external actors with appropriate authorisation.
    
*   Ability to [read state items](#retrieving-state-items) by both lava
    jobs and external actors with appropriate authorisation.

*   Support for Jinja rendering of state item values into job specifications at
    run-time.
    
The state manager handles any encoding / decoding required during the posting /
retrieval process.
