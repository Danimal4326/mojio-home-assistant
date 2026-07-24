# Vendored `mojio_sdk`

This directory is a **vendored copy** of the SDK from
<https://github.com/Danimal4326/mojio-py>. Do not edit it here.

It is vendored rather than declared in `manifest.json` `requirements` because
the Audi tenant support lives in a fork; the `mojio_sdk` package on PyPI is
owned by the upstream author and is still at 0.6.0.

It is imported relatively (`from .mojio_sdk.api import API`) so it can never
collide with a `mojio_sdk` installed from PyPI.

## Syncing

Re-copy from a checkout of the SDK repo and commit the result:

```bash
./scripts/sync_sdk.sh /path/to/mojio-py
```

Synced from: `bd946d3` (branch `feat/audi-tenant-support`)
