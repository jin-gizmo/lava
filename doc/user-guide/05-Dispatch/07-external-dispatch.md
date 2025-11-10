
## Direct Dispatch

The mechanism underlying the dispatch process is the placement of an
appropriately formatted message onto a specific worker fleet's SQS queue. Lava
provides a number interfaces for this purpose.

*   The [lava-dispatcher](#lava-dispatcher-utility) CLI utility.

*   A [Python interface](#python-dispatch-interface).

*   The lava GUI.

!!! warning
    **Do not** attempt to create your own dispatch messages for posting directly
    on the SQS worker queue. It will end in tears. Trust me on this.

### Python Dispatch Interface

The recommended way to generate a direct dispatch in Python is to use the lava
libraries. Refer to the API documentation for more information.

```python
from lava.lavacore import dispatch

run_id = dispatch(realm='...', job_id='...')
```
