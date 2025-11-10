
### exe

#### Error: job ... (...) failed: [Errno 8] Exec format error: '/tmp/lava/...'

This error indicates that the operating system tried to run a script as a binary
when it isn't. It generally means that the hashbang line is missing from the
beginning of a script file indicating what interpreter to use. For a Python
script it will look exactly like this:

```bash
#!/usr/bin/env python3
```

This error can also occur when an executable has been edited on a DOS system and
has acquired DOS CRLF line endings instead of UNIX LF line endings.
