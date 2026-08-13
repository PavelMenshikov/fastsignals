from fastsignals.links import jupiter_sell_url, jupiter_swap_url


def test_jupiter_url_contains_amount_and_slippage() -> None:
    url = jupiter_swap_url("TokenMint", 25, 0.5)
    assert url.endswith("-TokenMint?inAmount=25&slippage=0.5")


def test_jupiter_sell_url_uses_token_to_usdc_pair() -> None:
    url = jupiter_sell_url("TokenMint", 0.5)
    assert url.endswith("/TokenMint-EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v?slippage=0.5")
