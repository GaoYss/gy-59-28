from datetime import date, datetime

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Appointment, ExamBatch

batches_bp = Blueprint("batches", __name__, url_prefix="/api/batches")

VALID_PERIODS = {"上午", "下午"}
VALID_STATUSES = {"开放", "关闭"}


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def get_batch(timeslot):
    if timeslot in ["09:00-10:00", "10:30-11:30"]:
        return "上午"
    elif timeslot in ["14:00-15:00", "15:30-16:30"]:
        return "下午"
    return "其他"


@batches_bp.get("")
def list_batches():
    query = ExamBatch.query.order_by(ExamBatch.exam_date.asc(), ExamBatch.period.asc())
    batches = query.all()
    result = []
    for batch in batches:
        d = batch.to_dict()
        count = Appointment.query.filter(
            Appointment.exam_date == batch.exam_date,
            Appointment.timeslot.in_(
                ["09:00-10:00", "10:30-11:30"] if batch.period == "上午" else ["14:00-15:00", "15:30-16:30"]
            ),
            Appointment.status.in_(["已预约", "已确认", "已完成"]),
        ).count()
        attended = Appointment.query.filter(
            Appointment.exam_date == batch.exam_date,
            Appointment.timeslot.in_(
                ["09:00-10:00", "10:30-11:30"] if batch.period == "上午" else ["14:00-15:00", "15:30-16:30"]
            ),
            Appointment.status.in_(["已确认", "已完成"]),
        ).count()
        d["registered"] = count
        d["attended"] = attended
        d["attendanceRate"] = round(attended / count * 100, 1) if count > 0 else 0
        d["remaining"] = max(batch.capacity - count, 0)
        result.append(d)
    return jsonify(result)


@batches_bp.post("")
def create_batch():
    payload = request.get_json() or {}
    exam_date_str = payload.get("examDate", "").strip()
    period = payload.get("period", "").strip()
    capacity = payload.get("capacity")

    exam_date = parse_date(exam_date_str)
    if not exam_date:
        return jsonify({"message": "日期格式应为 YYYY-MM-DD"}), 400
    if period not in VALID_PERIODS:
        return jsonify({"message": "批次时段应为上午或下午"}), 400

    if exam_date < date.today():
        return jsonify({"message": "不能创建过去日期的批次"}), 400

    existing = ExamBatch.query.filter_by(exam_date=exam_date, period=period).first()
    if existing:
        return jsonify({"message": f"{exam_date_str} {period}批次已存在"}), 400

    cap = 30
    if capacity is not None:
        try:
            cap = int(capacity)
        except (TypeError, ValueError):
            return jsonify({"message": "容量应为整数"}), 400
        if cap < 1:
            return jsonify({"message": "容量不能小于1"}), 400

    batch = ExamBatch(exam_date=exam_date, period=period, capacity=cap, status="开放")
    db.session.add(batch)
    db.session.commit()
    return jsonify(batch.to_dict()), 201


@batches_bp.patch("/<int:batch_id>")
def update_batch(batch_id):
    batch = ExamBatch.query.get_or_404(batch_id)
    payload = request.get_json() or {}

    if "capacity" in payload:
        try:
            cap = int(payload["capacity"])
        except (TypeError, ValueError):
            return jsonify({"message": "容量应为整数"}), 400
        if cap < 1:
            return jsonify({"message": "容量不能小于1"}), 400
        batch.capacity = cap

    if "status" in payload:
        status = payload["status"]
        if status not in VALID_STATUSES:
            return jsonify({"message": "批次状态应为开放或关闭"}), 400
        batch.status = status

    db.session.commit()
    return jsonify(batch.to_dict())


@batches_bp.delete("/<int:batch_id>")
def delete_batch(batch_id):
    batch = ExamBatch.query.get_or_404(batch_id)
    count = Appointment.query.filter(
        Appointment.exam_date == batch.exam_date,
        Appointment.timeslot.in_(
            ["09:00-10:00", "10:30-11:30"] if batch.period == "上午" else ["14:00-15:00", "15:30-16:30"]
        ),
        Appointment.status.in_(["已预约", "已确认", "已完成"]),
    ).count()
    if count > 0:
        return jsonify({"message": "该批次下有有效预约，无法删除"}), 400
    db.session.delete(batch)
    db.session.commit()
    return jsonify({"message": "批次已删除"})


@batches_bp.get("/stats")
def batch_stats():
    start_date = parse_date(request.args.get("startDate"))
    end_date = parse_date(request.args.get("endDate"))

    query = ExamBatch.query.order_by(ExamBatch.exam_date.asc(), ExamBatch.period.asc())
    if start_date:
        query = query.filter(ExamBatch.exam_date >= start_date)
    if end_date:
        query = query.filter(ExamBatch.exam_date <= end_date)

    batches = query.all()
    result = []
    for batch in batches:
        timeslots = ["09:00-10:00", "10:30-11:30"] if batch.period == "上午" else ["14:00-15:00", "15:30-16:30"]
        appointments = (
            Appointment.query.filter(
                Appointment.exam_date == batch.exam_date,
                Appointment.timeslot.in_(timeslots),
            )
            .order_by(Appointment.timeslot.asc())
            .all()
        )
        registered = sum(1 for a in appointments if a.status in ["已预约", "已确认", "已完成"])
        attended = sum(1 for a in appointments if a.status in ["已确认", "已完成"])
        result.append(
            {
                "id": batch.id,
                "examDate": batch.exam_date.isoformat(),
                "period": batch.period,
                "capacity": batch.capacity,
                "status": batch.status,
                "registered": registered,
                "attended": attended,
                "attendanceRate": round(attended / registered * 100, 1) if registered > 0 else 0,
                "remaining": max(batch.capacity - registered, 0),
                "appointments": [a.to_dict() for a in appointments],
            }
        )
    return jsonify(result)
