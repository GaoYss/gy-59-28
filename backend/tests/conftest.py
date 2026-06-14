from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Appointment, ExamBatch, ExamQuestion, Makeup, Rule


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True


def _next_weekday_after(min_days):
    d = date.today() + timedelta(days=min_days)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


BATCH_DATE_1 = _next_weekday_after(4)
BATCH_DATE_2 = _next_weekday_after(8)


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        _seed_test_data()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _seed_test_data():
    rules = [
        Rule(subject="科目一", min_interval_days=3, max_daily_slots=2, allow_weekend=False, passing_score=90, makeup_wait_days=10, enabled=True),
        Rule(subject="科目二", min_interval_days=7, max_daily_slots=18, allow_weekend=False, passing_score=80, makeup_wait_days=10, enabled=True),
        Rule(subject="科目三", min_interval_days=10, max_daily_slots=15, allow_weekend=False, passing_score=90, makeup_wait_days=10, enabled=False),
    ]
    _db.session.add_all(rules)

    questions = [
        ExamQuestion(id=1, subject="科目一", question="题1", options=["A", "B", "C", "D"], answer="A"),
        ExamQuestion(id=2, subject="科目一", question="题2", options=["A", "B", "C", "D"], answer="B"),
        ExamQuestion(id=3, subject="科目一", question="题3", options=["A", "B", "C", "D"], answer="C"),
        ExamQuestion(id=4, subject="科目二", question="题4", options=["A", "B", "C", "D"], answer="D"),
    ]
    _db.session.add_all(questions)

    _db.session.add(
        ExamBatch(exam_date=BATCH_DATE_1, period="上午", capacity=2, status="开放")
    )
    _db.session.add(
        ExamBatch(exam_date=BATCH_DATE_1, period="下午", capacity=1, status="开放")
    )
    _db.session.add(
        ExamBatch(exam_date=BATCH_DATE_2, period="上午", capacity=30, status="关闭")
    )

    _db.session.commit()
