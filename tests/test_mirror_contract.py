"""Pure offline selection tests; no mirror runtime, key or provider access."""
import unittest
from app.backend.recovery import RESTORE_CONTRACT_VERSION,needs_restore_drill


class MirrorRestoreContract(unittest.TestCase):
    def current(self):
        return {'sha256':'same-archive','restoreContract':RESTORE_CONTRACT_VERSION,
                'restoreDrillPassed':True,'restoreDrillAt':'2026-10-29T15:00:00Z'}

    def test_unchanged_verified_archive_and_contract_can_reuse_its_drill(self):
        self.assertFalse(needs_restore_drill(self.current(),'same-archive',True))

    def test_changed_or_missing_contract_forces_drill_on_unchanged_archive(self):
        for value in [None,RESTORE_CONTRACT_VERSION-1]:
            with self.subTest(contract=value):
                state=self.current();state['restoreContract']=value
                self.assertTrue(needs_restore_drill(state,'same-archive',True))

    def test_changed_snapshot_or_missing_encrypted_target_forces_drill(self):
        self.assertTrue(needs_restore_drill(self.current(),'new-archive',True))
        self.assertTrue(needs_restore_drill(self.current(),'same-archive',False))

    def test_incomplete_prior_success_cannot_skip_drill(self):
        for field,value in [('restoreDrillPassed',False),('restoreDrillAt',None)]:
            with self.subTest(field=field):
                state=self.current();state[field]=value
                self.assertTrue(needs_restore_drill(state,'same-archive',True))
        self.assertTrue(needs_restore_drill({},'same-archive',True))


if __name__=='__main__':unittest.main(verbosity=2)
