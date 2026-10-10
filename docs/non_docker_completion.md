# Steps 2-5 while Docker is deferred

Update 2026-10-09: Docker is now installed and verified locally. Actual offline
inference, container API operations and mid-job persistent crash recovery passed;
see experiments/docker_verification.json. Historical deferred references below
describe the earlier stage. Remote HTTPS hosting remains pending.

## 2. Improve and evaluate the model

Training-only, five-fold template-group stress ablations compare unchanged
features, reference masking, resolved historical quote handling, C, and safety
class weights. Inner holdouts reproduce the actual deployed sigmoid calibration
configuration. The supplied validation set was already inspected and is now
explicitly a **development set**; a fresh independent set is needed for new
generalization claims.

The urgency study penalizes missed safety emergencies (cost 10), other urgency
misses (cost 5), and false alerts (cost 1). Its low-cutoff profile raises recall
but also false alerts. A separate balanced cutoff is selected by training-heldout
F1. Both profiles and their measured tradeoffs are retained; an improvement in
recall is not described as an improvement in every metric.

Actual experiment results: experiments/improvement/. Default model promotion is
recorded in promoted.json. Original release remains in artifacts/legacy, and the
recall-first alternative in artifacts/high_recall. Use ARTIFACT_DIR to select a
complete artifact/manifest pair, with a distinct version for each profile.

## 3. Test the actual browser UI

The private demo was tested in an isolated real Chrome browser using Playwright:
English/Sinhala/Tamil entry, CSV with Unicode and quoted newlines, actual async
progress, download, deletion/re-submission, errors, and mobile layout. Browser
screenshots and the report are in experiments/browser/. A short silent recording
is in output/rideeat_demo.webm. It is not the full narrated fifteen-minute video.

Reproduce with Node.js, the pinned package.json dependency and a local browser:

```powershell
npm install
npx playwright install chromium ffmpeg
$env:DEMO_USERNAME = 'demo'
$env:DEMO_PASSWORD = 'your-local-demo-password'
npm run test:browser
```

Start the backend/demo first, as shown in README. Browser tests use their own
ticket/job IDs; they do not touch evaluation jobs. Test recording contains
synthetic sample tickets, not real customer data or the backend API key.

## 4. Prepare/deploy public HTTPS

Native Python/systemd/Caddy deployment files and an installer are in deploy/.
Dedicated hosted lifecycle tests create and delete their own disposable jobs.
Read deploy/README.md, then provide approved server access, real DNS names, and
server-side credentials. No server or domain was provided; remote deployment
has not happened. Native deployment cannot prove the still-required identical
Docker image, so final container parity remains deferred.

## 5. Package and publish deliverables

Report/model card, detailed measured comparisons, video script, real silent
footage, source release archive and file SHA256 manifest are prepared. GitHub CI
workflow is included but has not run remotely. Official requirement PDFs are
still absent.

GitHub CLI is installed but signed out, and there is no configured remote. Sign
in normally and provide the intended existing repository URL. Publication script:

```powershell
gh auth login
.\scripts\publish_github.ps1 -RepositoryUrl 'https://github.com/OWNER/REPOSITORY'
```

OWNER/REPOSITORY is a placeholder, not a published URL. The script does not create
a repository, replace a different origin, or force-push. YouTube upload needs an
authenticated account and the full walkthrough recording. Actual external URLs
remain null in docs/submission_manifest.json until they are verified.
