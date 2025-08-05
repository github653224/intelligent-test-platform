from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_test_runs():
    return {"test_runs": []}
