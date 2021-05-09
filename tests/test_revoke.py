def test_revoke_strategy_from_vault(wbtc, wbtc_vault, wbtc_strategy, amount_wbtc, gov, user, strategist):
    # Deposit to the vault and harvest
    wbtc.approve(wbtc_vault, amount_wbtc, {"from": user})
    wbtc_vault.deposit(amount_wbtc, {"from": user})
    wbtc_strategy.harvest({"from": strategist})
    assert wbtc_strategy.estimatedTotalAssets()+1 == amount_wbtc


def test_revoke_strategy_from_strategy(wbtc, wbtc_vault, wbtc_strategy, amount_wbtc, gov, user, strategist):
    # Deposit to the vault and harvest
    wbtc.approve(wbtc_vault, amount_wbtc, {"from": user})
    wbtc_vault.deposit(amount_wbtc, {"from": user})
    wbtc_strategy.harvest({"from": strategist})
    assert wbtc_strategy.estimatedTotalAssets()+1 == amount_wbtc

    wbtc_strategy.setEmergencyExit()
    wbtc_strategy.harvest({"from": strategist})
    assert wbtc_strategy.estimatedTotalAssets() < 80 # Rounding error
    assert wbtc.balanceOf(wbtc_vault)+20 >= amount_wbtc * 0.994 # Account for 0.6% withdrawal fee. Give .000020 extra for precision
