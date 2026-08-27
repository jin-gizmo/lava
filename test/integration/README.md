# Integration Test Approach

This directory contains data-driven integration tests for Lava job execution.
The tests run real job specs through Lava runtime code and validate outcomes
with per-job checker modules.

## Scope

Unlike unit tests under `test/unit`, tests here focus on end-to-end handler
execution via `run_job` (`test_handler.py`), utilizing job specs augmentation
logic from core Lava code.

Custom assertions are implemented in checker modules under `test/checks`, which
are dynamically discoverable based on job spec paths. This allows test cases to
specify their own validation logic beyond simple pass/fail outcomes.

## Test Data Model

### Test metadata

Test metadata is defined under `x-lava-test` in job spec JSON, with the
following structure:

```yaml
x-lava-test:
  result: OK # required: OK or FAIL
  marks: 
    - local # required: at least one mark used by selection
  error_pattern: '^Failed with exit status \d+$'  # optional
```

Notes:

- `result` drives pass/fail expectation in `test_handler.py`.
- `marks` are matched by set intersection with `--test-mark` values.
- `error_pattern` is matched with `re.search()` against error raised when running the job if 
  present.

### Test data supplied to each test case

Each selected case is parametrized as one `x_lava_test` Python dictionary containing:
   - `check_path`: custom checker module path under `test/checks`
   - `job_spec`: parsed job JSON
   - `expected_result`: expected outcome (`OK` or `FAIL`)
   - `error_pattern`: optional regex expected for failure text

## Test case discovery and parametrization

Test cases are discovered in `test/conftest.py`.

1. `pytest_generate_tests()` checks for `x_lava_test` parameter in test function signatures, 
   parametrizes with cases from `load_test_assets()`. 
2. `load_test_assets()` scans `test/jobs/dist/<realm>` for `*.json` jobs generated from `make 
   dist -j dist env=<realm>`.
3. Jobs without `x-lava-test` field are ignored.
4. Jobs are filtered by `marks` under `x-lava-test` using `--test-mark`.
5. For each selected job, a test case dictionary is created based on the job spec and its path:
    - `check_path` is derived from the job spec path by replacing `test/jobs/dist` with `test/checks`
      and normalizing the file stem to a valid Python name (e.g. `hello-world.json` becomes 
      `hello_world.py`).
    - `job_spec` is the parsed JSON content of the job spec.
    - `expected_result` is taken from `x-lava-test.result`.
    - `error_pattern` is taken from `x-lava-test.error_pattern` if present.

## Checker Module

### Checker Mapping

Checker paths are derived from job spec paths by preserving relative directories
and normalizing file stems to valid Python names.

Example:

- Job spec: `test/jobs/dist/test/lava-jobs/cmd/hello-world.json`
- Checker: `test/checks/lava-jobs/cmd/hello_world.py`

### Checker Function Signature

Each checker module should expose a `check(...)` function:

```python
def check(
    job_spec,
    realm_info,
    job_result,
    job_events,
    job_error,
    fx,
    context,
):
	...
```

- `job_spec` is the parsed job JSON.
- `realm_info` is the realm information object from `augment_job_spec`.
- `job_result` is populated for successful runs.
- `job_events` is a list of log records captured during job execution.
- `job_error` is populated when `run_job` raises `LavaError`.
- `fx` provides dot-style fixture access (`FixtureAccessor` from `test/conftest.py`).
- `context` is a placeholder object for checker-local state.

## Logging Capture

Logs emittey during job execution are captured through monkeypatching Lava's
internal logger to append log records to a list. This allows checkers to perform
assertions on logs as part of their validation logic.

The captured logs are provided to checkers via the `job_events` parameter as a
dictionary of lists with keys on `(job_id, run_id)` pairs, similar to how log
events go into the DynamoDB events table. This is especially useful for a
`chain` job or a `foreach` job where we have parent-child job relationships.

For example, a `job_events` structure might look like:

```
{
    (parent_job, run_id_1): [record_1, record_2, ...],
    (child_job_1, run_id_2): [record_a, record_b, ...],
    ...
}
```

## Runtime Flow

For each parametrized case in `test_handler.py`:

1. Build a dispatch message (`make_dispatch_msg`).
2. Reload job from DynamoDB (`get_job_spec`) so optional fields are initialized.
3. Apply worker-side augmentation (`augment_job_spec`).
4. Execute via `run_job`.
5. Assert observed outcome vs `x-lava-test.result`.
6. If provided, assert `x-lava-test.error_pattern` against error text.
7. Run custom checker assertions from `check_path`.


