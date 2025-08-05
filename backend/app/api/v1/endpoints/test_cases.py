from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_test_cases():
    return {"test_cases": []}
