import json

import pytest

from votecastbench.uncertainty import bootstrap_report, load_organisation_ids


def test_paired_bootstrap_reports_intervals_and_rank_stability() -> None:
    report = bootstrap_report(
        [
            "baseline/last-ward-party-share",
            "openai/gpt-5.6-luna",
            "openai/other",
        ],
        ["q1", "q2", "q3"],
        [
            [0.4, 0.4, 0.4],
            [0.1, 0.2, 0.3],
            [0.3, 0.4, 0.5],
        ],
        replicates=1_000,
        seed=7,
    )
    rows = {row["model"]: row for row in report["forecasters"]}
    assert rows["openai/gpt-5.6-luna"]["probability_best_api_model"] == 1
    assert rows["openai/gpt-5.6-luna"]["api_rank_95_interval"] == [1, 1]
    assert rows["openai/other"]["brier_delta_vs_luna_95_interval"][0] >= 0
    assert report["resampling_unit"] == "question"
    assert report["organisation_count"] is None


def test_organisation_cluster_bootstrap_keeps_questions_together() -> None:
    report = bootstrap_report(
        [
            "baseline/last-ward-party-share",
            "openai/gpt-5.6-luna",
            "openai/other",
        ],
        ["q1", "q2", "q3"],
        [
            [0.4, 0.4, 0.4],
            [0.1, 0.2, 0.3],
            [0.3, 0.4, 0.5],
        ],
        replicates=100,
        seed=7,
        organisation_ids=["same-council", "same-council", "same-council"],
        accuracy_matrix=[
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
    )

    rows = {row["model"]: row for row in report["forecasters"]}
    assert report["resampling_unit"] == "organisation"
    assert report["organisation_count"] == 1
    assert report["method"] == "paired nonparametric cluster bootstrap over organisations"
    assert rows["openai/gpt-5.6-luna"]["brier_95_interval"] == pytest.approx([0.2, 0.2])
    assert rows["openai/gpt-5.6-luna"]["mean_top_choice_accuracy"] == 1
    assert rows["openai/gpt-5.6-luna"]["top_choice_accuracy_95_interval"] == [1, 1]


def test_load_organisation_ids_aligns_to_score_order(tmp_path) -> None:
    questions = tmp_path / "questions.jsonl"
    rows = [
        {"question_id": "q2", "election": {"organisation": "Council B"}},
        {"question_id": "q1", "election": {"organisation": "Council A"}},
    ]
    questions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    assert load_organisation_ids(questions, ["q1", "q2"]) == ["Council A", "Council B"]


def test_load_organisation_ids_rejects_missing_scored_question(tmp_path) -> None:
    questions = tmp_path / "questions.jsonl"
    questions.write_text(
        json.dumps({"question_id": "q1", "election": {"organisation": "Council A"}}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing scored question IDs"):
        load_organisation_ids(questions, ["q1", "q2"])
