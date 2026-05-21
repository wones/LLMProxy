from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from config.database import get_db
from models.log_model import RequestLog
from schemas.log_schema import LogResponse, LogListResponse, StatisticsResponse
from datetime import datetime, timezone

router = APIRouter(prefix="/api/logs", tags=["logs"])

def format_datetime_with_timezone(dt):
    """将UTC时间转换为本地时间字符串"""
    if dt is None:
        return None
    # SQLite不支持时区，所以我们假设存储的是UTC时间
    # 如果时间没有时区信息，我们需要手动添加UTC时区然后转换为本地时间
    if dt.tzinfo is None:
        # 添加UTC时区
        dt = dt.replace(tzinfo=timezone.utc)
    # 转换为本地时间
    dt = dt.astimezone()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    stats = db.query(
        func.count(RequestLog.id).label("total_calls"),
        func.sum(RequestLog.input_tokens).label("total_input_tokens"),
        func.sum(RequestLog.output_tokens).label("total_output_tokens"),
        func.avg(RequestLog.duration_ms).label("avg_duration_ms"),
        func.sum(case([(RequestLog.status_code == 200, 1)], else_=0)).label("success_count")
    ).first()
    
    total_calls = stats.total_calls or 0
    total_input_tokens = stats.total_input_tokens or 0
    total_output_tokens = stats.total_output_tokens or 0
    avg_duration_ms = int(stats.avg_duration_ms or 0)
    success_count = stats.success_count or 0
    success_rate = success_count / total_calls if total_calls > 0 else 0.0
    
    return StatisticsResponse(
        total_calls=total_calls,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_input_tokens + total_output_tokens,
        avg_duration_ms=avg_duration_ms,
        success_rate=success_rate
    )

@router.get("/")
async def get_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    request_type: str = Query(None),
    config_id: int = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(RequestLog)
    
    if request_type:
        query = query.filter(RequestLog.request_type == request_type)
    if config_id:
        query = query.filter(RequestLog.config_id == config_id)
    
    total = query.count()
    logs = query.order_by(RequestLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # 格式化日志中的时间
    formatted_logs = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "config_id": log.config_id,
            "request_type": log.request_type,
            "model_name": log.model_name,
            "status_code": log.status_code,
            "duration_ms": log.duration_ms,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "error_message": log.error_message,
            "request_headers": log.request_headers,
            "request_body": log.request_body,
            "response_body": log.response_body,
            "created_at": format_datetime_with_timezone(log.created_at)
        }
        formatted_logs.append(log_dict)
    
    return {"logs": formatted_logs, "total": total}

@router.get("/{id}", response_model=LogResponse)
async def get_log(id: int, db: Session = Depends(get_db)):
    log = db.query(RequestLog).filter(RequestLog.id == id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return log

@router.delete("/{id}")
async def delete_log(id: int, db: Session = Depends(get_db)):
    log = db.query(RequestLog).filter(RequestLog.id == id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    db.delete(log)
    db.commit()
    return {"message": "日志已删除"}
