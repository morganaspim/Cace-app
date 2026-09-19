# CACE Free Trial, One-Person Account, and Non-Destructive Expiry

Status: required production product/account policy.

## Product intent

CACE should be a full-featured production mathematics and sciences playground that "just works" for a normal user.

The free trial:

- requires no credit card;
- is granted once per verified person/user;
- is tied to a stable server-side person identity anchor, not merely a browser cookie or account row;
- cannot be reset by creating or deleting additional accounts.

If a returning person already has an account, CACE routes them to account recovery/merge rather than granting a new trial.

## Privacy-aware uniqueness

A production authentication adapter supplies a stable verified subject. CACE should derive/store an opaque person key rather than raw identity documents or provider credentials.

The trial entitlement ledger is separate from the ordinary account row so that deleting/recreating the account does not create a fresh trial.

Perfect "one human on Earth" identity proof is neither claimed nor required. The production policy uses the strongest reasonable verified identity anchor available to the deployment, with server-side rate/abuse controls and account recovery.

## After trial expiry

CACE must never behave like ransomware.

It must never:

- encrypt user files;
- corrupt/delete experiments;
- withhold export of user-owned data;
- disable account recovery;
- alter scientific evidence to force payment.

Expired unlicensed accounts enter a transparent limited mode. Users retain at least:

- sign in;
- view their own experiments/results;
- export/download their own data;
- delete their own data;
- account recovery/merge;
- help/documentation;
- license/subscription management.

Premium execution, premium compute, networked AI-economy actions, premium local-AI orchestration and other licensed features may be disabled until a valid license is activated.

## Scientific separation

Trial, payment, account and license state never changes scientific truth, verification state or proof qualification.
