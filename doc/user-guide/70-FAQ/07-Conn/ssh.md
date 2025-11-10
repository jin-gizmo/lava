
### ssh, scp, sftp

#### Authentication Failures

A possible cause of authentication failures is the default behaviour of ssh, scp
and sftp in situations where it cannot verify the fingerprint of the remote
host's public key. When this occurs, the client will drop into interactive mode
to ask for confirmation to accept the key, like so:

```
The authenticity of host 'sftp.xyzzy.com (192.219.1.1)' can't be established.
RSA key fingerprint is SHA256:TXYwAhoSEfm6Me6RtFHJRUEGL9lTuHqySI6GyxVe//M.
RSA key fingerprint is MD5:52:b4:70:1d:c1:0e:aa:4d:32:8e:f8:7a:cb:f9:b8:7e.
Are you sure you want to continue connecting (yes/no)?
```

Lava cannot handle this.

To avoid this problem, add `-o StrictHostKeyChecking=no` to the arguments when
invoking the connector script provided by lava.
