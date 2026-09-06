"""Unit tests for PromptAssembler."""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from aia_canvas.src.memory.profile_manager import ProfileManager
    from aia_canvas.src.memory.prompt_assembler import PromptAssembler
except ModuleNotFoundError:
    from memory.profile_manager import ProfileManager
    from memory.prompt_assembler import PromptAssembler


@pytest.fixture
def profile_manager(tmp_path: Path) -> ProfileManager:
    config_dir = tmp_path / "config"
    return ProfileManager(config_dir)


def test_initializes_with_and_without_profile_manager(profile_manager: ProfileManager):
    assembler_custom = PromptAssembler(profile_manager)
    assert assembler_custom.profile_manager is profile_manager
    assert "Aether" in assembler_custom.CORE_PERSONA

    assembler_default = PromptAssembler()
    assert assembler_default.profile_manager is not None


@pytest.mark.parametrize(
    "text,expected_tokens",
    [
        ("", 0),
        ("a", 1),
        ("hey", 1),
        ("1234", 1),
        ("12345678", 2),
        ("a" * 40, 10),
    ],
)
def test_estimate_tokens(text: str, expected_tokens: int):
    assert PromptAssembler._estimate_tokens(text) == expected_tokens


def test_assembles_valid_system_prompt(profile_manager: ProfileManager):
    profile_manager.update_active_project("canvas_v2")
    profile_manager.push_hot_topic("shaders")
    profile_manager.push_hot_topic("physics")
    profile_manager.sync_staged_nodes([{"title": "CardA.qml"}, {"title": "CardB.qml"}])

    assembler = PromptAssembler(profile_manager)
    prompt = assembler.assemble_system_prompt()

    # Core Persona
    assert assembler.CORE_PERSONA in prompt

    # Ground Truth Section
    assert "[GROUND TRUTH MEMORY]" in prompt
    assert "- Environment:" in prompt
    assert "Linux" in prompt
    assert "- Style:" in prompt
    assert "direct_authentic_peer" in prompt
    assert "- Known Entities:" in prompt

    # Active Working State Section
    assert "[ACTIVE WORKING STATE]" in prompt
    assert "- Current Objective / Project: canvas_v2" in prompt
    assert "- Hot Topics: shaders, physics" in prompt
    assert "- Staged Nodes: CardA.qml, CardB.qml" in prompt

    # Focal Context should not be present when not supplied
    assert "[FOCAL CONTEXT]" not in prompt


def test_injects_focal_nodes_correctly(profile_manager: ProfileManager):
    assembler = PromptAssembler(profile_manager)
    focal_nodes = [
        {"title": "TelemetryView.qml"},
        {"name": "EngineWorker.py"},
    ]

    prompt = assembler.assemble_system_prompt(focal_nodes=focal_nodes)

    assert "[FOCAL CONTEXT]" in prompt
    assert "- In Clearing: TelemetryView.qml, EngineWorker.py" in prompt

    assert assembler.format_focal_context([]) == ""
    assert assembler.format_focal_context(None) == ""


@pytest.mark.parametrize(
    "budget",
    [1300, 600, 300, 150, 50],
)
def test_enforces_hard_token_ceiling_with_oversized_nodes(
    profile_manager: ProfileManager, budget: int
):
    assembler = PromptAssembler(profile_manager)

    # 100 oversized dummy nodes
    oversized_nodes = [
        {
            "node_id": f"node_{i}",
            "title": f"OversizedFocalNode_{i}_" + ("lorem_ipsum_dolor_sit_amet_" * 20),
            "path": f"/deeply/nested/path/to/large/virtual/canvas/node_{i}.qml",
        }
        for i in range(100)
    ]

    # Staged nodes in profile are also populated
    profile_manager.sync_staged_nodes(oversized_nodes[:20])
    profile_manager.update_active_project("deep_stress_test_project")

    prompt = assembler.assemble_system_prompt(focal_nodes=oversized_nodes, max_tokens=budget)
    estimated = assembler._estimate_tokens(prompt)

    assert estimated <= budget


def test_trimming_priority_order(profile_manager: ProfileManager):
    assembler = PromptAssembler(profile_manager)
    focal_nodes = [{"title": "FocalAlpha"}, {"title": "FocalBeta"}]

    # 1. High budget: all sections present
    prompt_full = assembler.assemble_system_prompt(focal_nodes=focal_nodes, max_tokens=1300)
    assert "[GROUND TRUTH MEMORY]" in prompt_full
    assert "[ACTIVE WORKING STATE]" in prompt_full
    assert "[FOCAL CONTEXT]" in prompt_full

    # 2. Moderate budget: focal context trimmed/dropped before working state
    gt_tokens = assembler._estimate_tokens(assembler.format_ground_truth())
    core_tokens = assembler._estimate_tokens(assembler.CORE_PERSONA)
    tight_budget = core_tokens + gt_tokens + 25

    prompt_tight = assembler.assemble_system_prompt(
        focal_nodes=focal_nodes, max_tokens=tight_budget
    )
    assert assembler._estimate_tokens(prompt_tight) <= tight_budget
    assert "[GROUND TRUTH MEMORY]" in prompt_tight


@pytest.mark.parametrize(
    "identity_payload,working_payload",
    [
        ({}, {}),
        (
            {"entities": None, "system_environment": None, "collaboration_style": None},
            {"active_project": None, "hot_topics": None, "staged_nodes": None},
        ),
        (
            {"entities": "plain_string", "system_environment": "custom_os"},
            {"active_project": "", "hot_topics": ["single"], "staged_nodes": ["simple_node"]},
        ),
    ],
)
def test_handles_empty_profiles_and_missing_keys_gracefully(
    profile_manager: ProfileManager, identity_payload: dict, working_payload: dict
):
    profile_manager.save_identity(identity_payload)
    profile_manager.save_working_state(working_payload)

    assembler = PromptAssembler(profile_manager)

    gt_block = assembler.format_ground_truth(identity_payload)
    assert "[GROUND TRUTH MEMORY]" in gt_block

    ws_block = assembler.format_working_state(working_payload)
    assert "[ACTIVE WORKING STATE]" in ws_block

    prompt = assembler.assemble_system_prompt()
    assert assembler.CORE_PERSONA in prompt
    assert "[GROUND TRUTH MEMORY]" in prompt
    assert "[ACTIVE WORKING STATE]" in prompt

