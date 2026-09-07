# Packaging

The source manifest hashes every delivered source/config/test/document file.
The standalone HTML is rebuilt from that tree. CI packages the tested tree and
machine-readable outputs, then a separate unpack/build/test step verifies it.

Old partial payloads in masar-deploy/payload are historical recovery evidence and
are not a production boot dependency. No database, credentials, backup snapshot,
node_modules, Python wheels, virtual environment or font file belongs in the source
release. ZIP SHA-256 and exact commit are reported alongside the final artifact,
not hard-coded as an unverified value here.
