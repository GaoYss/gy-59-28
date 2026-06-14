from datetime import date, timedelta

from tests.conftest import _next_weekday_after


class TestMakeupWaitDays:
    def test_create_makeup_without_scheduled_date_allowed(self, client):
        resp = client.post("/api/makeups", json={
            "studentName": "王五",
            "originalSubject": "科目一",
            "failedScore": 85,
        })
        assert resp.status_code == 201
        assert resp.get_json()["scheduledDate"] is None

    def test_create_makeup_with_scheduled_date_before_wait_days_rejected(self, client):
        too_early = (date.today() + timedelta(days=5)).isoformat()
        resp = client.post("/api/makeups", json={
            "studentName": "王五",
            "originalSubject": "科目一",
            "failedScore": 85,
            "scheduledDate": too_early,
        })
        assert resp.status_code == 400
        assert "补考日期需至少在 10 天后" in resp.get_json()["message"]

    def test_create_makeup_with_scheduled_date_after_wait_days_allowed(self, client):
        ok_date = _next_weekday_after(15).isoformat()
        resp = client.post("/api/makeups", json={
            "studentName": "王五",
            "originalSubject": "科目一",
            "failedScore": 85,
            "scheduledDate": ok_date,
        })
        assert resp.status_code == 201
        assert resp.get_json()["scheduledDate"] == ok_date

    def test_update_makeup_with_scheduled_date_before_wait_days_rejected(self, client):
        resp = client.post("/api/makeups", json={
            "studentName": "赵六",
            "originalSubject": "科目一",
            "failedScore": 85,
        })
        assert resp.status_code == 201
        makeup_id = resp.get_json()["id"]

        too_early = (date.today() + timedelta(days=3)).isoformat()
        resp2 = client.patch(f"/api/makeups/{makeup_id}", json={
            "scheduledDate": too_early,
        })
        assert resp2.status_code == 400
        assert "补考日期需至少在 10 天后" in resp2.get_json()["message"]

    def test_update_makeup_with_scheduled_date_after_wait_days_allowed(self, client):
        resp = client.post("/api/makeups", json={
            "studentName": "赵六",
            "originalSubject": "科目一",
            "failedScore": 85,
        })
        assert resp.status_code == 201
        makeup_id = resp.get_json()["id"]

        ok_date = _next_weekday_after(12).isoformat()
        resp2 = client.patch(f"/api/makeups/{makeup_id}", json={
            "scheduledDate": ok_date,
        })
        assert resp2.status_code == 200
        assert resp2.get_json()["scheduledDate"] == ok_date

    def test_create_makeup_respects_subject_specific_wait_days(self, client):
        too_early = (date.today() + timedelta(days=8)).isoformat()
        resp = client.post("/api/makeups", json={
            "studentName": "孙七",
            "originalSubject": "科目二",
            "failedScore": 75,
            "scheduledDate": too_early,
        })
        assert resp.status_code == 400
        assert "补考日期需至少在 10 天后" in resp.get_json()["message"]

    def test_create_makeup_on_boundary_wait_days_allowed(self, client):
        boundary = (date.today() + timedelta(days=10)).isoformat()
        resp = client.post("/api/makeups", json={
            "studentName": "周八",
            "originalSubject": "科目一",
            "failedScore": 85,
            "scheduledDate": boundary,
        })
        assert resp.status_code == 201
        assert resp.get_json()["scheduledDate"] == boundary
