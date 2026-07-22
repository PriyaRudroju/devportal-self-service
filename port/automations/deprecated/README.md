# Deprecated automations (pre Lambda-first flow)

These automations supported the original architecture where Port native approval
(`requiredApproval: true`) drove Teams notifications and catalog updates.

The revised flow uses:

- Self-service action **WEBHOOK** → Lambda `POST /ec2/request`
- Lambda UPSERTs catalog entity and sends Teams notification
- Lambda `GET /approval-decision` UPSERTs approved/rejected
- [`../trigger-github-on-ec2-approved.json`](../trigger-github-on-ec2-approved.json) triggers GitHub after approval

**Do not import** these files into Port for new setups. Disable or delete them if
already published.
