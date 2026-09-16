# Roadmap

This is a prioritized backlog, not a promise of delivery dates. The [feature matrix](FEATURE_STATUS.md) distinguishes implemented code from unverified integrations.

## Release verification

- [ ] Run the full Docker suite and PostgreSQL/Redis CI job on an accessible engine.
- [ ] Exercise production TLS, secrets and first-start provisioning on staging.
- [ ] Perform backup restoration, rollback drills and sustained write/failure tests.
- [ ] Scan container images and pin reviewed deployment digests.
- [ ] Complete manual screen-reader and broader populated/error-state reviews.

## AI quality

- [ ] Add independent, multilingual and adversarial retrieval evaluations.
- [ ] Validate actual configured hosted model loops, budgets and latency.
- [ ] Expand compatibility knowledge and disclose unverified dimensions.
- [ ] Evaluate review-analysis quality with realistic, consented data.

## Product and operations

- [ ] Self-service identity recovery and business tenant isolation.
- [ ] Supplier onboarding, tax documents and catalog ingestion.
- [ ] Real payment/carrier integration with authenticated webhooks and reconciliation.
- [ ] Alert ownership, retention/deletion policy and audit tamper evidence.
- [ ] HA stores and tested cluster deployment when justified by scale.

## Repository stewardship

- [ ] Select an application-code license.
- [ ] Resolve the two retailer UPS photo reuse permissions before commercial deployment.
- [ ] Configure private vulnerability reporting and branch protection.
