from fastapi import APIRouter, Depends

from app.dependencies.integration import require_integration_hmac

router = APIRouter(tags=["Integration"])


@router.post("/integration/echo")
def integration_echo(
    payload: dict,
    auth: dict[str, str] = Depends(require_integration_hmac),
) -> dict:
    return {
        "ok": True,
        "key_id": auth["key_id"],
        "echo": payload,
    }
