import brownie
from brownie import Contract
from helpers import stratData,vaultData


def test_operation(accounts, token, vault, live_strategy, strategy, strategist, amount, user, user2, want_pool, chain, gov, vsp):
    one_day = 86400
    chain.snapshot()
    
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) >= amount
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)

    # harvest 1: funds from vault -> strat
    live_strategy.harvest({"from": gov}) # Do this just bc this strategy needs to empty its funds
    strategy.harvest({"from": strategist})
    chain.mine(1)
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    assert strategy.estimatedTotalAssets()+1 >= 0
    
    # Harvest 2: Allow rewards to be earned
    print("\n**Harvest 2: check for profits**")
    before_balance = strategy.estimatedTotalAssets()
    chain.sleep(one_day)
    chain.mine(1)
    after_rewards = strategy.estimatedTotalAssets()
    
    print("\nEst APR: ", "{:.2%}".format(
            ((after_rewards - before_balance) * 365) / (before_balance)
        )
    )
    assert before_balance < after_rewards
    strategy.harvest({"from": strategist})
    chain.sleep(3600 * 6) # Unlock profits
    chain.mine(1)
    after_balance = strategy.estimatedTotalAssets()
    after_withdraw_fee = before_balance * 0.94
    print("before_balance:", before_balance)
    print("after_balance:", after_balance)
    assert after_balance > before_balance * 0.94
    # Harvest 3
    print("\n**Check Profitable Withdraw**")
    chain.sleep(3600) # wait six hours for a profitable withdraw
    strategy.harvest({"from": strategist})
    vault.withdraw(vault.balanceOf(user),user,61,{"from": user}) # Need more loss protect to handle 0.6% withdraw fee
    print("deposit amount:", amount)
    print("withdrawn amount:", token.balanceOf(user))
    after_withdraw_fee = amount * 0.94
    print("after_withdraw_fee:", after_withdraw_fee)
    # We want to calculate against the post fee amount because depending
    # On when test is run, rewards contract may have limited emissions
    assert token.balanceOf(user) > after_withdraw_fee

    # Check DEX toggle
    originalDex = strategy.activeDex()
    strategy.toggleActiveDex({"from": gov})
    newDex = strategy.activeDex()
    assert originalDex != newDex
    strategy.toggleActiveDex({"from": gov})

    # Update debt ratio
    print("\n**Check Debt Ratio Change**")
    before_balance = strategy.estimatedTotalAssets()
    vault.updateStrategyDebtRatio(strategy.address, 10, {"from": gov}) # 1%
    strategy.harvest({"from": strategist})
    print("before_balance:", before_balance)
    print("after_balance:", strategy.estimatedTotalAssets())
    assert before_balance > strategy.estimatedTotalAssets()
    stratData(strategy, token, want_pool, vsp)
    

    # Set funds to 0
    print("\nTokens before:", token.balanceOf(strategy)/1e6)
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    assert strategy.estimatedTotalAssets() < 1e12 # allow for some dust

    # set emergency and exit
    vault.updateStrategyDebtRatio(strategy, 1_000, {"from": gov})
    strategy.harvest({"from": strategist})
    strategy.setEmergencyExit()
    strategy.harvest({"from": strategist})