import logging
import threading


class Worker:
    def __init__(self, store, predictor):
        self.store = store
        self.predictor = predictor
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name='tensorforge-worker', daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=10)

    def run(self):
        while not self.stop_event.is_set():
            job_id = self.store.claim()
            if job_id is None:
                self.stop_event.wait(.05)
                continue
            offset = 0
            try:
                while not self.stop_event.is_set():
                    tickets = self.store.items(job_id, offset)
                    if not tickets:
                        break
                    predictions = self.predictor.predict_many(tickets)
                    if not self.store.commit_chunk(job_id, offset, predictions):
                        break
                    offset += len(predictions)
            except Exception:
                logging.error('Background inference failed for job %s', job_id)
                self.store.fail(job_id)
