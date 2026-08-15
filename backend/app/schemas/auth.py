from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginPendingResponse(BaseModel):
    message: str
    email: str


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str
    purpose: Literal["verification", "login"] = "verification"
    # Required when purpose="login": a correct OTP alone must never be enough
    # to issue a full session on its own — anyone who can read a "login OTP"
    # email (e.g. a temporarily-exposed inbox) would otherwise get in with no
    # password at all. Unused/ignored for purpose="verification".
    password: Optional[str] = None


class ResendOtpRequest(BaseModel):
    email: EmailStr
    purpose: Literal["verification", "login"] = "verification"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class RoleOut(BaseModel):
    vertical: str
    role: str
    rep_id: Optional[str] = None


class UserOut(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: str
    google_id: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    merchant_id: Optional[str] = None
    # Every UserMerchantRole row for merchant_id — the minimum groundwork the
    # team-permissions page needs ("what am I allowed to do here") without a
    # second round trip. Populated in routes/auth.py's /me handler.
    roles: list[RoleOut] = []
    company: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    primary_currency: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    totp_enabled: bool = False
    # Set once POST /auth/delete-account has been called, cleared by
    # /delete-account/cancel — lets the Privacy & Data tab render a
    # "deletion pending" state instead of the delete button after a re-login.
    deletion_requested_at: Optional[datetime] = None


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    primary_currency: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code_base64: str


class TwoFactorCodeRequest(BaseModel):
    code: str


class TwoFactorDisableRequest(BaseModel):
    current_password: str


class TwoFactorVerifyLoginRequest(BaseModel):
    email: EmailStr
    password: str
    code: str


class SessionOut(BaseModel):
    id: int
    device: Optional[str] = None
    ip_address: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_current: bool = False


class LoginEventOut(BaseModel):
    id: str
    when: datetime
    device: Optional[str] = None
    ip_address: Optional[str] = None
    result: Literal["success", "blocked"]
    reason: Optional[str] = None
