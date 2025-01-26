from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from data_module import DataAPI
from app.api import deps

router = APIRouter()

@router.get("/list")
async def get_fund_list(
    fund_type: Optional[str] = None,
    data_api: DataAPI = Depends(deps.get_data_api)
):
    """获取基金列表"""
    try:
        funds = data_api.get_fund_list(fund_type)
        return {"status": "success", "data": funds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{fund_code}")
async def get_fund_info(
    fund_code: str,
    data_api: DataAPI = Depends(deps.get_data_api)
):
    """获取基金详细信息"""
    try:
        info = data_api.get_fund_info(fund_code)
        if not info:
            raise HTTPException(status_code=404, detail="基金不存在")
        return {"status": "success", "data": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 