from fastapi import APIRouter, Depends
from app.core.auth import AuthContext, require_menu
from .service import GradeInput, assess
from . import service

router = APIRouter(prefix='/v1/self-study', tags=['自考题库'])
guard = require_menu('self_study')

@router.get('/grading-status')
def grading_status(_: AuthContext = Depends(guard)):
    return {'enabled':bool(service.settings().deepseek_api_key), 'provider':'DeepSeek',
            'notice':'仅在点击 AI 评分时发送本题题目、参考答案和作答；AI 分数仅供练习参考，可手动改分。'}

@router.post('/grade')
def grade_answer(payload: GradeInput, user: AuthContext = Depends(guard)):
    return assess(payload, user.username)
