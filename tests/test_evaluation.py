from docagent.evaluation import contains_term, normalize, score_answer, wilson


def test_numeric_scoring_does_not_accept_wrong_magnitude_or_negative():
    assert contains_term(normalize("最多12人"), "12")
    assert not contains_term(normalize("最多112人"), "12")
    assert not contains_term(normalize("12.5人"), "12")
    assert not contains_term(normalize("-12"), "12")
    assert contains_term(normalize("上午08:00至22:00"), "08:00")


def test_failed_task_is_not_counted_as_correct_abstention():
    case = {"answerable": False, "expected_evidence_ids": []}
    result = {"state": "failed", "answer": {"answer": "failed", "status": "insufficient", "evidence": []}}
    assert not score_answer(case, result)["rule_correct"]
    result["state"] = "completed"
    assert score_answer(case, result)["rule_correct"]


def test_cross_section_question_requires_all_terms_and_evidence():
    case = {"answerable": True, "expected_answer": "12 and 20", "required_terms": ["12", "20"],
            "expected_evidence_ids": ["s1", "s2"]}
    result = {"state": "completed", "answer": {"answer": "12", "status": "answered", "evidence": [{"id": "s1"}]}}
    score = score_answer(case, result)
    assert not score["rule_correct"]
    assert score["expected_evidence_recall"] == 0.5
    result["answer"]["answer"] = "12 and 20"
    assert score_answer(case, result)["rule_correct"]
    assert not score_answer(case, result)["all_expected_evidence"]


def test_small_perfect_sample_still_has_uncertainty():
    low, high = wilson(30, 30)
    assert 0.88 < low < 0.90
    assert high == 1.0
