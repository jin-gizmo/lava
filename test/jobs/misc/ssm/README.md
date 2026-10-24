# SSM Parameters

This directory contains SSM parameter specs. These are YAML files in the format
required by the **ssmp** utility.

This directory is repo safe because secrets must be contained in a `.env` file.
**Ssmp` will refuse to load `SecureString` parameters unless the value is a pure
environment variable reference.
