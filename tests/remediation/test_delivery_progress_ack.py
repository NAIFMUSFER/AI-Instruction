"""Real isolated-worker witness: account for each call before outbound work."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from acs_generation_job import JobRunner
from acs_plan_review import PlanError


def synthetic_outbound(marker, durable=None):
    from acs_provider_budget import limited,consume
    with limited(1):
        consume()  # Must synchronously cross durable progress admission first.
        Path(marker).write_text('synthetic outbound work')
        return durable is None or Path(durable).exists()


class DurableProgress(unittest.TestCase):
    def test_failed_durable_accounting_prevents_outbound_work(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=str(Path(directory)/'sent')
            def reject(event):
                time.sleep(.05)
                raise PlanError('STORE_UNAVAILABLE','synthetic accounting unavailable')
            runner=JobRunner(executor='process')
            with self.assertRaises(PlanError):
                runner.run('test_delivery_progress_ack:synthetic_outbound',{'marker':marker},on_progress=reject)
            self.assertFalse(Path(marker).exists(),'child started outbound work before durable ACK')
            self.assertEqual(runner.stats()['failed'],1)
            self.assertEqual(runner.in_flight(),0)

    def test_outbound_work_observes_committed_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=str(Path(directory)/'sent');durable=str(Path(directory)/'accounted')
            def accept(event):
                time.sleep(.05)
                Path(durable).write_text(json.dumps(event))
            result=JobRunner(executor='process').run('test_delivery_progress_ack:synthetic_outbound',{'marker':marker,'durable':durable},on_progress=accept)
            self.assertTrue(result)
            self.assertEqual(json.loads(Path(durable).read_text())['provider_calls'],1)

    def test_expired_job_never_acknowledges_new_outbound_work(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=str(Path(directory)/'sent')
            began=[]
            def slow(event):began.append(True);time.sleep(2.1)
            with self.assertRaises(TimeoutError):
                JobRunner(executor='process').run('test_delivery_progress_ack:synthetic_outbound',{'marker':marker},on_progress=slow,timeout_s=2)
            self.assertTrue(began)
            self.assertFalse(Path(marker).exists())

if __name__=='__main__':unittest.main()
