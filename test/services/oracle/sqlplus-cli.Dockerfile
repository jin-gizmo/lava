# This is a heavy duty way just to get sqlplus but since we have this image for
# the DB server anyway, this is a reasonable approach.
FROM gvenzl/oracle-free:full
ENTRYPOINT ["sqlplus"]
