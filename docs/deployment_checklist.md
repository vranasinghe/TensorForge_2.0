# Deployment and submission checklist

## Local evidence

- [x] Actual supervised model artifact and SHA256 manifest exist.
- [x] Dataset audit, train-only comparisons and measured validation results exist.
- [x] Seven API operations and original-schema validation are implemented.
- [x] Single-instance durable SQLite jobs, cancellation and restart handling are implemented.
- [x] Private backend-connected demo and CSV import/export are implemented.
- [x] Offline in-process inference test script exists; check PROGRESS for execution result.
- [x] Docker image built; offline Unicode inference, actual API lifecycle, and persistent mid-job crash/restart passed. Evidence: experiments/docker_verification.json.
- [ ] Reference 2-vCPU/4-GB measurements: local benchmarks are not equivalent.

## Container

Build: `docker build -t tensorforge:local .`.

Required invocation: `docker run -p 8000:8000 -e API_KEY=<key> tensorforge:local`.
Use an environment injection mechanism rather than storing the actual evaluation
key in shell scripts, Docker layers, Git or reports.

Persist jobs: add `-v tensorforge-jobs:/srv/runtime`. Named-volume ownership must
allow the image's nonroot user to write. Mount the same volume across process or
container restarts. Replacing an unmounted container destroys its job state.

Offline smoke: `sh scripts/test_offline.sh tensorforge:local` disables container
network and executes inference inside it. Host-port integration is a separate
test on a normal container; publishing a port with --network none is not that test.

## Hosting

- [ ] Obtain approved hosting account and deployment credentials.
- [ ] Deploy the same image and artifact at stable public HTTPS with valid TLS.
- [ ] Configure evaluation API_KEY only in server environment.
- [ ] Use one service worker and one replica; keep a persistent SQLite volume.
- [ ] Put the private demo behind valid HTTPS and separate username/password; never use the evaluation key as the demo password.
- [ ] No CORS origins are enabled for the API. Demo browser uses same-origin private proxy. Add origins only when an actual client requires them.
- [ ] Verify health within 120 seconds and matching versions in every operation.
- [ ] Run authenticated smoke with BACKEND_URL and API_KEY from environment; test async lifecycle using dedicated disposable job IDs.
- [ ] Confirm disk retention, volume permissions, startup recovery and expiry.

## Deliverables

- [ ] Obtain missing official guidelines and build-guide PDFs; verify deliverable requirements.
- [ ] Export report and confirm the master document's five-page limit against official guidelines.
- [ ] Publish authorized GitHub repository; no publication performed yet.
- [ ] Record and upload unlisted video; no YouTube action performed yet.
- [ ] Submit accessible demo/API/repository/video links and private key through the organizers' approved channel.
- [ ] Team review and signoff.

Hosted API URL, demo URL, GitHub URL and YouTube URL: all pending.
Model quality, especially Sinhala and safety false negatives, remains a material
limitation. Contract robustness does not establish production readiness.
