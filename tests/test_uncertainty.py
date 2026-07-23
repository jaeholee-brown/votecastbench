from votecastbench.uncertainty import bootstrap_report


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
