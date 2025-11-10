
## Posting State Items

State items can be posted via the following mechanisms:

*   The [state](#action-type-state) action type.

*   The [lava state API](#the-lava-state-api).

*   The [lava state utility](#lava-state-utility).

Posting an item will create a new item or completely replace an existing item,
as appropriate.

!!! info
    Do not create state items with a `state_id` starting with `lava`.
    This prefix is reserved.

The lava state manager does not support incremental update of an existing state
item.
