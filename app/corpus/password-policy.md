# Password Policy

All company accounts require a password manager-generated password of at least 16 characters,
or a passphrase of at least 20 characters if memorized.

## Multi-Factor Authentication

MFA is mandatory on all systems handling Restricted data (see `data-security.md` for the
classification). MFA is strongly recommended, but not mandatory, on systems handling only
Internal or Public data.

## Rotation

Passwords do not expire on a fixed schedule. Rotation is required only after a suspected
compromise, reported through `incident-response.md`.
