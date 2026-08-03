"""Robotics-AR 核心模块导出。 / Public exports for the Robotics-AR core."""

from .canonical import canonical_bytes, canonical_json, sha256_bytes, sha256_obj, ensure_finite
from .models import (
    FORBIDDEN_CORE_FIELDS,
    Budget,
    make_candidate_action,
    make_charter,
    make_decision,
    make_evidence,
    make_hypothesis,
    make_research_question,
    make_unknown,
    validate_core_object,
)
from .event_log import EventLog, TAKEOVER_EVENT_TYPES
from .agent_protocol import (
    AgentProtocolError,
    PathPolicy,
    RawEvidenceGuard,
    WriterLease,
    build_expert_profiles,
    make_agent_receipt,
    synthesize_expert_rounds,
    validate_agent_receipt,
    build_dynamic_expert_profiles,
)
from .real_robot import OneShotRealRobotToken, RealRobotGateError, build_caution_document
from .workflow import SupervisedWorkflow, WorkflowError
from .takeover import TakeoverManager, TakeoverError, build_intake, initialize_takeover
from .project_core import ProjectCoreError, compile_project_core, validate_project_core
from .project_audit import ProjectAuditError, audit_project
from .history_reconstruction import DoNotRepeatRegistry, ExperimentLedger, HistoryError, reconstruct_history
from .baseline import BaselineError, compile_baseline_spec, reproduce_baseline
from .trial_contract import TrialContractError, TrialContractManager, compile_trial_contract
from .trial_queue import TrialQueue, TrialQueueError, build_proposal, validate_trial_id
from .trial_loop import TrialDecisionEngine, TrialLoop, TrialLoopError
from .best_known import BestKnownState, BestKnownError, build_candidate
from .blackboard import Blackboard, BlackboardError
from .batch_controller import BatchController, BatchControllerError, compile_batch
from .user_correction import UserCorrectionError, compile_correction, confirm_and_resume
from .reporting_v3 import write_checkpoint_artifacts, write_current_handoff, write_current_report
from .migration import migrate_project, migrate_session_state
from .schema_validation import SchemaValidationError, validate_artifact
from .environment import validate_environment_receipt

__all__ = [
    "Budget",
    "EventLog",
    "TAKEOVER_EVENT_TYPES",
    "FORBIDDEN_CORE_FIELDS",
    "canonical_bytes",
    "canonical_json",
    "ensure_finite",
    "make_candidate_action",
    "make_charter",
    "make_decision",
    "make_evidence",
    "make_hypothesis",
    "make_research_question",
    "make_unknown",
    "sha256_bytes",
    "sha256_obj",
    "validate_core_object",
    "AgentProtocolError",
    "PathPolicy",
    "RawEvidenceGuard",
    "WriterLease",
    "build_expert_profiles",
    "make_agent_receipt",
    "synthesize_expert_rounds",
    "validate_agent_receipt",
    "build_dynamic_expert_profiles",
    "OneShotRealRobotToken",
    "RealRobotGateError",
    "build_caution_document",
    "SupervisedWorkflow",
    "WorkflowError",
    "TakeoverManager",
    "TakeoverError",
    "build_intake",
    "initialize_takeover",
    "ProjectCoreError",
    "compile_project_core",
    "validate_project_core",
    "ProjectAuditError",
    "audit_project",
    "DoNotRepeatRegistry",
    "ExperimentLedger",
    "HistoryError",
    "reconstruct_history",
    "BaselineError",
    "compile_baseline_spec",
    "reproduce_baseline",
    "TrialContractError",
    "TrialContractManager",
    "compile_trial_contract",
    "TrialQueue",
    "TrialQueueError",
    "build_proposal",
    "validate_trial_id",
    "TrialDecisionEngine",
    "TrialLoop",
    "TrialLoopError",
    "BestKnownState",
    "BestKnownError",
    "build_candidate",
    "Blackboard",
    "BlackboardError",
    "BatchController",
    "BatchControllerError",
    "compile_batch",
    "UserCorrectionError",
    "compile_correction",
    "confirm_and_resume",
    "write_checkpoint_artifacts",
    "write_current_handoff",
    "write_current_report",
    "migrate_project",
    "migrate_session_state",
    "SchemaValidationError",
    "validate_artifact",
    "validate_environment_receipt",
]
