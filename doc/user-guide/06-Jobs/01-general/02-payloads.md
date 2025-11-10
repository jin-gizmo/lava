
## Job Payloads

Some job types have some kind of associated payload. Payloads are specified by
the mandatory `payload` field in the [job specification](#the-jobs-table).

Payloads are job type specific and can be of the following types:

*   **[S3 based payloads](#s3-payloads)**: The `payload` field will point to
    location(s) in S3 that the lava worker will download at run-time. These are
    typically things such as code bundles, SQL scripts etc.

*   **Inline payloads**: The `payload` field will contain the actual payload.
    These may be things like single CLI commands, small in-line SQL scripts,
    docker repository names etc.

*   **No payload**: Some job types (e.g. [log](#job-type-log)) don't require a
    payload and hence the value of the `payload` field is ignored. (As an
    accident of history, the field is still required but it can be set to
    anything. A value of `--` or `null` is common usage.)

### S3 Payloads

Prior to version 7.1.0
([Pichincha](https://en.wikipedia.org/wiki/https://en.wikipedia.org/wiki/Pichincha_(volcano))),
the S3 payload downloader was the [v1 downloader](#the-v1-payload-downloader).

As of version 7.1.0
([Pichincha](https://en.wikipedia.org/wiki/https://en.wikipedia.org/wiki/Pichincha_(volcano))),
there is an additional [v2 downloader](#the-v2-payload-downloader).

Only one version of the downloader is active on any lava worker.

!!! info
    As of version 8.1.0 ([Kīlauea](https://en.wikipedia.org/wiki/Kīlauea)), the
    [v2 downloader](#the-v2-payload-downloader) is the default and the
    [v1 downloader](#the-v1-payload-downloader) is deprecated.

The [v1 downloader](#the-v1-payload-downloader) can be enabled by setting the
[`PAYLOAD_DOWNLOADER`](#general-configuration-parameters) worker configuration
parameter to `v1`. See [Lava Worker Configuration](#lava-worker-configuration)
for more details.

#### The v1 Payload Downloader

The v1 S3 payload downloader requires the `payload` field in the [job
specification](#the-jobs-table) to be a string that specifies a location in S3
relative to the `s3_payloads` area defined in the [realms](#the-realms-table)
table. It can be either:

* an S3 object key, in which case a single S3 object is downloaded; or

* an S3 prefix ending in `/`, in which case all objects under that prefix will
  be downloaded and made available to the job in lexicographic order.

!!! info
    The download process when a prefix is specified does not recurse down the
    object hierarchy in S3. All objects to be downloaded must sit directly under
    that prefix. The job will abort with an error if there are any sub-prefixes.

A typical job specification might contain something like this:

```json
{
  "payload": "app/whatever/query-some-stuff.sql"
}
```

... or this:

```json
{
  "payload": "app/whatever/lots-of-sqls/"
}
```

#### The v2 Payload Downloader

If the  `payload` field in the [job specification](#the-jobs-table) is a string,
the v2 S3 payload downloader behaves the same as the 
[v1 downloader](#the-v1-payload-downloader), with one minor exception. If the
string is a prefix containing sub-prefixes, the
[v1 downloader](#the-v1-payload-downloader) aborts with an error whereas the
[v2 downloader](#the-v2-payload-downloader) silently ignores the sub-prefixes.

In v2, the `payload` field may also be a list of strings. These are processed
in the specified order, using the same mechanism as the
[v1 downloader](#the-v1-payload-downloader) and the combined list of downloaded
objects is made available to the job. The download process does not recurse into
sub-prefixes which are silently ignored.

!!! info
    Lava places the files resulting from each item in the list in a separate
    private directory to avoid name clashes. There is no way a payload file can
    know the location of any other payload file that isn't part of the same list
    item.
