from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.database import get_db
from models.config_model import LLMConfig
from schemas.config_schema import ConfigCreate, ConfigUpdate, ConfigResponse

router = APIRouter(prefix="/api/configs", tags=["configs"])

@router.get("/", response_model=list[ConfigResponse])
async def get_all_configs(db: Session = Depends(get_db)):
    configs = db.query(LLMConfig).all()
    return configs

@router.get("/active", response_model=list[ConfigResponse])
async def get_active_configs(db: Session = Depends(get_db)):
    configs = db.query(LLMConfig).filter(LLMConfig.is_active == True).order_by(LLMConfig.created_at.asc()).all()
    return configs

@router.get("/current", response_model=ConfigResponse)
async def get_current_config(db: Session = Depends(get_db)):
    config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
    if not config:
        raise HTTPException(status_code=404, detail="没有激活的配置")
    return config

@router.get("/{id}", response_model=ConfigResponse)
async def get_config(id: int, db: Session = Depends(get_db)):
    config = db.query(LLMConfig).filter(LLMConfig.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config

@router.post("/", response_model=ConfigResponse)
async def create_config(config: ConfigCreate, db: Session = Depends(get_db)):
    db_config = LLMConfig(
        name=config.name,
        target_url=config.target_url,
        app_key=config.app_key,
        app_secret=config.app_secret,
        detection_type=config.detection_type,
        detection_id=config.detection_id,
        stream=config.stream,
        is_active=False
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.put("/{id}", response_model=ConfigResponse)
async def update_config(id: int, config_update: ConfigUpdate, db: Session = Depends(get_db)):
    db_config = db.query(LLMConfig).filter(LLMConfig.id == id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    if config_update.name is not None:
        db_config.name = config_update.name
    if config_update.target_url is not None:
        db_config.target_url = config_update.target_url
    if config_update.app_key is not None:
        db_config.app_key = config_update.app_key
    if config_update.app_secret is not None:
        db_config.app_secret = config_update.app_secret
    if config_update.detection_type is not None:
        db_config.detection_type = config_update.detection_type
    if config_update.detection_id is not None:
        db_config.detection_id = config_update.detection_id
    if config_update.stream is not None:
        db_config.stream = config_update.stream
    
    db.commit()
    db.refresh(db_config)
    return db_config

@router.delete("/{id}")
async def delete_config(id: int, db: Session = Depends(get_db)):
    db_config = db.query(LLMConfig).filter(LLMConfig.id == id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db.delete(db_config)
    db.commit()
    return {"message": "配置已删除"}

@router.post("/{id}/toggle")
async def toggle_config(id: int, db: Session = Depends(get_db)):
    db_config = db.query(LLMConfig).filter(LLMConfig.id == id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db_config.is_active = not db_config.is_active
    db.commit()
    db.refresh(db_config)
    return {"message": "配置状态已更新", "is_active": db_config.is_active}
