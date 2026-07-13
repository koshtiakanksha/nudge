from pydantic import BaseModel


class LinkTokenResponse(BaseModel):
    link_token: str
    mock_mode: bool = False


class ExchangePublicTokenRequest(BaseModel):
    public_token: str
    institution_name: str | None = None


class PlaidItemOut(BaseModel):
    id: str
    institution_name: str
    accounts: list[dict]
    last_synced_at: str | None = None


class SyncResponse(BaseModel):
    new_transactions: int
    accounts_synced: int
    mock_mode: bool = False
