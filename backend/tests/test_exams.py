from app.models import ExamRecord, Makeup


class TestExamPassNoMakeup:
    def test_passed_exam_creates_no_makeup(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "张三",
            "subject": "科目一",
            "answers": {"1": "A", "2": "B", "3": "C"},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["passed"] is True
        assert data["makeup"] is None

        with app.app_context():
            assert Makeup.query.count() == 0
            assert ExamRecord.query.count() == 1


class TestExamFailGeneratesMakeup:
    def test_failed_exam_creates_makeup(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "李四",
            "subject": "科目一",
            "answers": {"1": "B", "2": "A", "3": "D"},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["passed"] is False
        assert data["makeup"] is not None
        assert data["makeup"]["status"] == "待安排"
        assert "未达合格线" in data["makeup"]["notes"]
        assert data["makeup"]["failedScore"] == data["record"]["score"]

        with app.app_context():
            makeup = Makeup.query.first()
            assert makeup is not None
            assert makeup.original_subject == "科目一"
            assert makeup.student_name == "李四"

    def test_partial_fail_still_generates_makeup(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "王五",
            "subject": "科目一",
            "answers": {"1": "A", "2": "A", "3": "D"},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        score = data["record"]["score"]
        assert score < 90
        assert data["record"]["passed"] is False
        assert data["makeup"] is not None

    def test_makeup_wait_days_recorded(self, client, app):
        resp = client.post("/api/exams/submit", json={
            "studentName": "赵六",
            "subject": "科目二",
            "answers": {"4": "A"},
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["record"]["passed"] is False
        assert data["makeup"]["originalSubject"] == "科目二"
