"""Data generator routes exposed as efficiency tools."""

from fastapi import APIRouter, Depends

from app.core.auth import AuthContext, require_menu
from app.core.config import get_settings
from app.modules.data_generator.schemas import DataGenerateRequest, DataGenerateResponse
from app.modules.data_generator.service import generate_id_cards, generate_phone_numbers


router = APIRouter(tags=["数据生成"])


@router.post("/v1/tools/data-generator", response_model=DataGenerateResponse, summary="生成实用测试数据")
def generate_data(payload: DataGenerateRequest, _: AuthContext = Depends(require_menu("data_generator"))):
    """Generate synthetic values or return explicitly configured receivers."""
    if payload.kind == "id_card":
        rows = generate_id_cards(
            payload.count,
            gender=payload.gender,
            min_birth_year=payload.min_birth_year,
            max_birth_year=payload.max_birth_year,
        )
        warning = "身份证号码仅为规则校验通过的合成数据，不对应或证明任何真实身份。"
    else:
        rows = generate_phone_numbers(
            payload.count,
            mode=payload.phone_mode,
            configured_numbers=get_settings().test_sms_phone_numbers,
        )
        if payload.phone_mode == "configured_receivers":
            warning = "号码来自服务端配置的受控号码；收信能力仍取决于运营商和供应商配置。"
        elif payload.phone_mode == "twilio_magic":
            warning = "Twilio 魔术号码只模拟 API 校验，不会收到真实短信。"
        else:
            warning = "随机号码仅保证格式，可能与真实号码碰撞，禁止拨打或发送短信。"
    return DataGenerateResponse(rows=rows, warning=warning)
