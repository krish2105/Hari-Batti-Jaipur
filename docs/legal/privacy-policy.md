# Privacy policy

> **DRAFT – requires lawyer review.** Written for the Digital Personal Data Protection Act, 2023 and the DPDP Rules,
> 2025 (most duties apply from 13 May 2027). The operator ("Data Fiduciary") and Grievance Officer are to be named
> before any public launch.

## Summary
HariBatti shows traffic-signal countdowns and helps traffic police audit signal timing. It is read-only: it never
controls a signal. We collect as little personal data as possible and delete it on a fixed schedule.

## What we collect, why, and for how long

| Who | Data | Purpose | Kept for |
| --- | --- | --- | --- |
| Website visitors | Nothing personal. No cookies for tracking, no analytics, no third-party trackers | — | — |
| Mobile app users | Location **only while a ride or walk is running**, on the phone; never uploaded outside a study | Countdowns and speed advice | Not stored by us |
| App users who report a signal | Report type, junction or map point, optional note (no name, no phone number) | Fixing signals | Until resolved + 1 year |
| Field-study volunteers (with written consent) | Random participant ID, vehicle type, GPS at 1 Hz during test runs only (first and last 200 m removed) | Measuring whether advice reduces stops | Raw traces deleted after **30 days**; only aggregate results kept |
| Officers and customer staff | Work email, role, sign-in times, actions such as exports and notes | Access control and audit trail | Account life; audit log 1 year |
| Junction videos (police/customer supplied) | Faces and number plates are blurred **before** anything is stored | Counting vehicles and measuring signal timing | Raw video deleted after **30 days** |

Sign-in codes are stored only as hashes and deleted a day after they expire. We do no automatic number-plate
recognition and no face recognition. We do not sell or share personal data for advertising.

## Where data is stored
In India only (production hosting in an Indian cloud region). Police feed data belongs to the police and stays in the
tenant it came from.

## Your rights
You can ask for a copy of your data, a correction, or erasure. Signed-in users: Signal Command → your account →
"Export my data" / "Erase my data" (API: `GET /privacy/me/export`, `POST /privacy/requests`). We answer within 30 days.
Erasure replaces your email with an anonymous code everywhere it appears. You may complain to the Grievance Officer
(to be named) and then to the Data Protection Board of India.

## Children
The app is not meant for children under 18; field studies accept adult drivers only.

## Security
Encryption in transit (HTTPS), encrypted disks and backups in production, least-privilege access, audit logs.
See SECURITY.md.

## Changes
We will post changes here with a date and, for material changes, tell signed-in users.
