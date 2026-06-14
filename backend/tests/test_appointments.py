from datetime import date, timedelta

from app.models import Appointment, ExamBatch, Rule
from tests.conftest import BATCH_DATE_1, BATCH_DATE_2


def _next_weekday_after(min_days):
    d = date.today() + timedelta(days=min_days)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _valid_payload(**overrides):
    payload = {
        "studentName": "王五",
        "idNumber": "320101199901010022",
        "subject": "科目一",
        "examDate": BATCH_DATE_1.isoformat(),
        "timeslot": "09:00-10:00",
    }
    payload.update(overrides)
    return payload


class TestDailySlotsFull:
    def test_reject_when_daily_slots_exhausted(self, client, app):
        with app.app_context():
            rule = Rule.query.filter_by(subject="科目一").first()
            for i in range(rule.max_daily_slots):
                from app.extensions import db
                db.session.add(Appointment(
                    student_name=f"学员{i}",
                    id_number=f"id_{i}",
                    subject="科目一",
                    exam_date=BATCH_DATE_1,
                    timeslot="09:00-10:00",
                    status="已预约",
                ))
            db.session.commit()

        resp = client.post("/api/appointments", json=_valid_payload())
        assert resp.status_code == 400
        data = resp.get_json()
        assert "名额已满" in data["message"]


class TestBatchCapacityFull:
    def test_reject_when_batch_capacity_exhausted(self, client, app):
        with app.app_context():
            batch = ExamBatch.query.filter_by(exam_date=BATCH_DATE_1, period="下午").first()
            assert batch is not None
            for i in range(batch.capacity):
                from app.extensions import db
                db.session.add(Appointment(
                    student_name=f"下午学员{i}",
                    id_number=f"pm_id_{i}",
                    subject="科目二",
                    exam_date=BATCH_DATE_1,
                    timeslot="14:00-15:00",
                    status="已预约",
                ))
            db.session.commit()

        resp = client.post("/api/appointments", json=_valid_payload(
            subject="科目二", examDate=BATCH_DATE_1.isoformat(), timeslot="15:30-16:30"
        ))
        assert resp.status_code == 400
        data = resp.get_json()
        assert "名额已满" in data["message"] or "批次" in data["message"]


class TestDuplicateAppointment:
    def test_reject_duplicate_active_appointment(self, client, app):
        resp = client.post("/api/appointments", json=_valid_payload())
        assert resp.status_code == 201

        resp2 = client.post("/api/appointments", json=_valid_payload())
        assert resp2.status_code == 400
        data = resp2.get_json()
        assert "已有同科目有效预约" in data["message"]

    def test_allow_after_cancellation(self, client, app):
        resp = client.post("/api/appointments", json=_valid_payload())
        assert resp.status_code == 201
        appt_id = resp.get_json()["id"]

        client.patch(f"/api/appointments/{appt_id}", json={"status": "已取消"})

        resp2 = client.post("/api/appointments", json=_valid_payload())
        assert resp2.status_code == 201


class TestWeekendNotAllowed:
    def test_reject_weekend_when_rule_disallows(self, client, app):
        today = date.today()
        days_to_sat = (5 - today.weekday()) % 7
        if days_to_sat == 0:
            days_to_sat = 7
        saturday = today + timedelta(days=days_to_sat)
        if saturday < date.today() + timedelta(days=4):
            saturday += timedelta(days=7)

        resp = client.post("/api/appointments", json=_valid_payload(examDate=saturday.isoformat()))
        assert resp.status_code == 400
        data = resp.get_json()
        assert "周末" in data["message"]


class TestPastDate:
    def test_reject_past_date(self, client):
        resp = client.post("/api/appointments", json=_valid_payload(examDate="2020-01-01"))
        assert resp.status_code == 400
        data = resp.get_json()
        assert "过去" in data["message"]


class TestMinIntervalDays:
    def test_reject_too_soon(self, client):
        too_soon = (date.today() + timedelta(days=1)).isoformat()
        resp = client.post("/api/appointments", json=_valid_payload(examDate=too_soon))
        assert resp.status_code == 400
        data = resp.get_json()
        assert "提前" in data["message"]


class TestSubjectNotEnabled:
    def test_reject_disabled_subject(self, client):
        resp = client.post("/api/appointments", json=_valid_payload(
            subject="科目三", examDate=BATCH_DATE_2.isoformat()
        ))
        assert resp.status_code == 400
        data = resp.get_json()
        assert "未开放" in data["message"]


class TestBatchClosed:
    def test_reject_closed_batch(self, client, app):
        with app.app_context():
            closed_batch = ExamBatch.query.filter_by(exam_date=BATCH_DATE_2, status="关闭").first()
            assert closed_batch is not None

        resp = client.post("/api/appointments", json=_valid_payload(
            subject="科目二", examDate=BATCH_DATE_2.isoformat(), timeslot="09:00-10:00"
        ))
        assert resp.status_code == 400
        data = resp.get_json()
        assert "关闭" in data["message"]


class TestMissingFields:
    def test_reject_missing_student_name(self, client):
        payload = _valid_payload()
        del payload["studentName"]
        resp = client.post("/api/appointments", json=payload)
        assert resp.status_code == 400
        assert "缺少" in resp.get_json()["message"]

    def test_reject_empty_payload(self, client):
        resp = client.post("/api/appointments", json={})
        assert resp.status_code == 400


class TestInvalidTimeslot:
    def test_reject_invalid_timeslot_avoiding_batch_capacity(self, client, app):
        with app.app_context():
            from app.extensions import db
            from app.models import ExamBatch
            batch = ExamBatch.query.filter_by(exam_date=BATCH_DATE_1, period="上午").first()
            for i in range(batch.capacity):
                from app.models import Appointment
                db.session.add(Appointment(
                    student_name=f"满员学员{i}",
                    id_number=f"full_id_{i}",
                    subject="科目一",
                    exam_date=BATCH_DATE_1,
                    timeslot="09:00-10:00",
                    status="已预约",
                ))
            db.session.commit()

        resp = client.post("/api/appointments", json=_valid_payload(
            timeslot="12:00-13:00"
        ))
        assert resp.status_code == 400
        assert "无效时段" in resp.get_json()["message"]

    def test_reject_random_timeslot(self, client):
        resp = client.post("/api/appointments", json=_valid_payload(
            timeslot="半夜两点"
        ))
        assert resp.status_code == 400
        assert "无效时段" in resp.get_json()["message"]

    def test_reject_empty_timeslot(self, client):
        resp = client.post("/api/appointments", json=_valid_payload(
            timeslot=""
        ))
        assert resp.status_code == 400
        assert "缺少字段" in resp.get_json()["message"]
