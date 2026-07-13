from datetime import date, timedelta

from app.services.plaid_service import plaid_service


def test_plaid_mock_mode():
    assert plaid_service.mock_mode is True


def test_create_link_token_mock():
    result = plaid_service.create_link_token("user123")
    assert result["mock_mode"] is True
    assert "link_token" in result


def test_exchange_and_accounts_mock():
    exchange = plaid_service.exchange_public_token("fake-public-token")
    assert "access_token" in exchange and "item_id" in exchange

    accounts = plaid_service.get_accounts(exchange["access_token"])
    assert len(accounts) >= 1
    assert all("balance" in a for a in accounts)


def test_get_transactions_mock_generates_data():
    exchange = plaid_service.exchange_public_token("fake-public-token")
    end = date.today()
    start = end - timedelta(days=30)
    txns = plaid_service.get_transactions(exchange["access_token"], start, end)
    assert isinstance(txns, list)
    for t in txns:
        assert "plaid_transaction_id" in t
        assert "amount" in t
        assert start <= t["date"] <= end
