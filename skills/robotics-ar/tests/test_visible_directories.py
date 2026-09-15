"""验证可见目录、项目边界与旧会话。 / Test visible paths, project boundaries, and legacy sessions."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from robotics_ar_core.atomic_io import AtomicIOError, atomic_write_json, runtime_root, project_output_directory, output_policy
from robotics_ar_core.reporting_v3 import write_checkpoint_artifacts
from robotics_ar_core.session import SessionManager
from robotics_ar_core.agent_protocol import PathPolicy, AgentProtocolError
from robotics_ar_core.history_reconstruction import reconstruct_history
from robotics_ar_core.project_audit import audit_project


class VisibleDirectoryTests(unittest.TestCase):
    def test_hidden_authorization_is_explicit_and_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with output_policy(allow_hidden_directories=True):
                atomic_write_json(root / '.authorized' / 'state.json', {})
                with self.assertRaises(AtomicIOError):
                    project_output_directory(root, '../escape')
            self.assertTrue((root / '.authorized/state.json').exists())
            with self.assertRaises(AtomicIOError):
                atomic_write_json(root / '.unauthorized' / 'state.json', {})

    def test_reports_are_opt_in_without_per_task_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager = SessionManager(root)
            manager.initialize(mode='PLANNING_ONLY', interaction_language='zh')
            self.assertEqual(write_checkpoint_artifacts(manager), (None, None))
            self.assertFalse(manager.paths.root_report.exists())
            with output_policy(reports_requested=True):
                write_checkpoint_artifacts(manager)
                write_checkpoint_artifacts(manager)
            previous = manager.paths.root_report.read_bytes()
            self.assertEqual(write_checkpoint_artifacts(manager), (None, None))
            self.assertEqual(previous, manager.paths.root_report.read_bytes())
            self.assertFalse(list(manager.paths.reports.glob('*.md')))

    def test_audit_default_keeps_evidence_without_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = audit_project(root)
            target = Path(result['output_dir'])
            self.assertTrue((target / 'audit-receipt.json').exists())
            self.assertFalse(list(target.glob('*.md')))
            with output_policy(reports_requested=True):
                audit_project(root)
            self.assertTrue((target / 'repository-map.md').exists())

    def test_new_session_has_no_hidden_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager = SessionManager(root)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh")
            self.assertEqual(manager.paths.root, root / "robotics-ar")
            self.assertFalse(any(p.name.startswith('.') for p in root.rglob('*') if p.is_dir()))

    def test_legacy_resume_and_dual_root_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager = SessionManager(root)
            manager.initialize(mode="PLANNING_ONLY", interaction_language="zh")
            manager.paths.root.rename(root / '.robotics-ar')
            self.assertEqual(SessionManager(root).state['session_id'], manager.state['session_id'])
            self.assertEqual(runtime_root(root), root / '.robotics-ar')
            (root / 'robotics-ar').mkdir()
            with self.assertRaises(AtomicIOError):
                runtime_root(root)

    def test_hidden_output_and_escape_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for candidate in ('.tmp/output', 'robotics-ar/.cache', '../escape'):
                with self.assertRaises(AtomicIOError):
                    project_output_directory(root, candidate)
            with self.assertRaises(AtomicIOError):
                atomic_write_json(root / '.tmp' / 'result.json', {})
            for operation in (audit_project, reconstruct_history):
                with self.assertRaises(AtomicIOError):
                    operation(root, output_dir=root / '.scratch')
            self.assertEqual(list(root.iterdir()), [])

    def test_agent_policy_blocks_hidden_parent_but_allows_dot_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy = PathPolicy.create(root, allowed_paths=['.'])
            with self.assertRaises(AgentProtocolError):
                policy.assert_write('.worktrees/test/file.py')
            self.assertEqual(policy.assert_write('.gitignore'), root / '.gitignore')
            (root / '.existing').mkdir()
            self.assertEqual(policy.assert_write('.existing/config'), root / '.existing/config')


if __name__ == '__main__':
    unittest.main()
