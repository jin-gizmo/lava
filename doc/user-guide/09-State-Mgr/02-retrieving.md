
## Retrieving State Items

State items can be retrieved via the following mechanisms:

*   [Real-time retrieval during job initialisation](#state-item-retrieval-during-job-initialisation).

*   The [lava state API](#the-lava-state-api).

*   The [lava state utility](#lava-state-utility).

The retrieval process uses DynamoDB [strongly consistent reads](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html).

!!! note
    While this gives more reliability in state item availability, it does require
    higher throughput on the [state table](#the-state-table).

### State Item Retrieval During Job Initialisation { data-toc-label="Retrieval During Job Initialisation" }

When a job is run, an initialisation procedure populates elements of the
[job specification](#the-jobs-table) to produce the
[augmented job specification](#the-augmented-job-specification). As part of this
process, lava expands the `state` element of the job specification, if present.
This element is a map of state item IDs (state_id) and default values. If a
state_id is present in the [state](#the-state-table) table, the value will be
extracted and used to replace the default value in the job specification. The
resulting map is then made available to the [Jinja rendering
process](#jinja-rendering-in-lava) used to prepare the job.

This means, for example, that one job can post a state item (e.g. using an
[on_success](#job-actions) job action) that lava will then automatically make
available to another job via the Jinja renderer.

Neat eh?

The state map can be referenced in a Jinja expression as `job.state` or via the
shorthand `state`. A state item with a `state_id` of `my_state_id` can then be
referenced in a Jinja expression using any of the following equivalents:

```jinja2
{{ job.state.my_state_id }}
{{ job.state['my_state_id'] }}
{{ state.my_state_id }}
{{ state['my_state_id'] }}
```

The square brackets variant is required when `my_state_id` is not a valid
Python identifier.
