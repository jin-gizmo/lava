These resources need to be sync'd to S3 so the build process can find them
there rather than trying to upload them each time. This is because they tend to
be large and relatively static so there is no point copying them to the packer
build instance each time.

The process of syncing to S3 is performed by the packer builder using a local
provisioner. All you need to do is make sure that this directory is properly
populated (via real files or symlinks to files).
