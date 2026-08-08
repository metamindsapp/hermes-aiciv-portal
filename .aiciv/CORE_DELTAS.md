# AiCIV upstream delta ledger

AiCIV uses Hermes extension points first. Changes to upstream Hermes source are allowed when a product requirement cannot be satisfied correctly through the public theme/plugin contract.

For every upstream-source change, record the path, reason, protected behavior, tests, sync risk, and whether a generic upstream hook could replace it later.

## Current upstream-source changes

None in the initial product layer. The Living Record theme and AiCIV workspace are currently implemented through the dashboard extension contract.

A later branded-distribution change may be needed to lock the approved AiCIV theme and remove product-inappropriate theme selection. That change should be added here only if the public extension surface cannot enforce the brand requirement.
