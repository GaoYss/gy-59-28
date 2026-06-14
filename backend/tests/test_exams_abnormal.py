from app.models import ExamRecord, Makeup


class TestMissingRequiredFields:
    def test_reject_missing_student_name(self, client):
        resp = client.post("/api/exams/submit", json={
            "subject": "科目一",
            "answers": {"1": "A"},
        })
        assert resp.status_code == 400
        assert "请提交" in resp.get_json()["message"]

    def test_reject_missing_subject(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "answers": {"1": "A"},
        })
        assert resp.status_code == 400

    def test_reject_missing_answers(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
        })
        assert resp.status_code == 400

    def test_reject_empty_student_name(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "   ",
            "subject": "科目一",
            "answers": {"1": "A"},
        })
        assert resp.status_code == 400


class TestNonDictAnswers:
    def test_reject_answers_as_list(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": ["A", "B"],
        })
        assert resp.status_code == 400

    def test_reject_answers_as_string(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": "ABC",
        })
        assert resp.status_code == 400

    def test_reject_answers_as_number(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": 123,
        })
        assert resp.status_code == 400


class TestInvalidQuestionIds:
    def test_reject_nonexistent_question_ids(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": {"9999": "A", "8888": "B"},
        })
        assert resp.status_code == 400
        assert "没有可评分的题目" in resp.get_json()["message"]


class TestEmptyAnswers:
    def test_empty_answers_dict_returns_400(self, client):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": {},
        })
        assert resp.status_code == 400
        assert "没有可评分的题目" in resp.get_json()["message"]


class TestAbnormalAnswerValues:
    def test_wrong_answer_value_still_scores(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": {"1": "Z", "2": "???", "3": ""},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["score"] == 0
        assert data["record"]["passed"] is False
        assert data["makeup"] is not None

        with app.app_context():
            record = ExamRecord.query.first()
            assert record.correct_count == 0
            assert len(record.details) == 3

    def test_null_answer_value_treated_as_wrong(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "李四",
            "subject": "科目一",
            "answers": {"1": None, "2": "B", "3": None},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["correctCount"] == 1
        assert data["record"]["passed"] is False

    def test_mixed_valid_and_invalid_ids(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "王五",
            "subject": "科目一",
            "answers": {"1": "A", "9999": "B", "2": "B"},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["totalQuestions"] == 2
        assert data["record"]["correctCount"] == 2
        assert data["record"]["score"] == 100
        assert data["record"]["passed"] is True
        assert data["makeup"] is None
