from fastapi import APIRouter, Request

from app.dependencies import ContainerDep, CurrentUserDep, auth_service
from app.schemas.auth import LoginRequest, MeOut, RefreshRequest, TokenOut
from app.schemas.common import ApiResponse, ok
from app.utils.rate_limit import client_ip

router = APIRouter()


@router.post("/login", response_model=ApiResponse[TokenOut])
def login(
    payload: LoginRequest, request: Request, container: ContainerDep
) -> ApiResponse[TokenOut]:
    login_id = payload.login_id
    container.login_limiter.hit(f"ip:{client_ip(request)}")
    container.login_limiter.hit(f"login:{login_id.lower()}")
    return ok(auth_service(container).login(login_id, payload.password))


@router.post("/refresh", response_model=ApiResponse[TokenOut])
def refresh(
    payload: RefreshRequest, request: Request, container: ContainerDep
) -> ApiResponse[TokenOut]:
    container.login_limiter.hit(f"ip:{client_ip(request)}")
    return ok(auth_service(container).refresh(payload.refresh_token))


@router.get("/me", response_model=ApiResponse[MeOut])
def me(user: CurrentUserDep, container: ContainerDep) -> ApiResponse[MeOut]:
    return ok(auth_service(container).me(user))
