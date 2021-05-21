import brownie
from brownie import Contract
from helpers import stratData,vaultData


def test_operation(StrategyVesper, accounts, token, vault, live_strategy, strategy, uni_router, sushi_router, strategist, amount, user, pool_rewards, user2, vToken, want_pool, chain, gov, vsp):
    one_day = 86400
    chain.snapshot()
    #live_strategy.harvest({"from": gov}) # Do this just bc this strategy needs to empty its funds
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) >= amount
    vaultData(vault, token)
    stratData(strategy, token, vToken, vsp)

    # harvest 1: funds from vault -> strat
    strategy.harvest({"from": strategist})
    chain.mine(1)
    vaultData(vault, token)
    stratData(strategy, token, vToken, vsp)
    assert strategy.estimatedTotalAssets()+1 >= 0
    
    # Harvest 2: Allow rewards to be earned
    print("\n**Harvest 2: check for profits**")
    before_balance = strategy.estimatedTotalAssets() + token.balanceOf(vault)
    chain.sleep(one_day*20)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    chain.sleep(3600 * 6) # Unlock profits
    chain.mine(1)
    print("Loss Protection Balance:", strategy.lossProtectionBalance())
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()
    
    after_balance = strategy.estimatedTotalAssets() + token.balanceOf(vault)
    print("before_balance:", before_balance)
    print("after_balance:", after_balance)
    assert after_balance > before_balance

    # Harvest 3
    print("\n**Check Profitable Withdraw**")
    strategy.harvest({"from": strategist})
    chain.sleep(3600) # wait six hours for a profitable withdraw
    # Let's put our strategy to front of the queue so that we can test impact by withdraws
    vault.withdraw(vault.balanceOf(user),user,61,{"from": user}) # Need more loss protect to handle 0.6% withdraw fee
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()
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
    vault.updateStrategyDebtRatio(strategy.address, 50, {"from": gov}) # 5%
    strategy.harvest({"from": strategist})
    # ^ Anytime we reduce debtRatio then harvest, we suffer _loss 
    # because of withdrawFee. Here the debtRatio actually goes below target
    # because of penalty on loss
    after_balance = strategy.estimatedTotalAssets()
    print("before_balance:", before_balance)
    print("after_balance:", strategy.estimatedTotalAssets())
    assert before_balance > after_balance
    stratData(strategy, token, vToken, vsp)
    

    # Set funds to 0
    print("\nTokens before:", token.balanceOf(strategy)/1e8)
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, vToken, vsp)
    assert strategy.estimatedTotalAssets() < 1e12 # allow for some dust
    vault.updateStrategyDebtRatio(strategy, 1_000, {"from": gov})
    strategy.harvest({"from": strategist})
    est_assets_before = strategy.estimatedTotalAssets()
    vaultData(vault, token)
    stratData(strategy, token, vToken, vsp)
    print("\nTest Migrate:")
    # migrate to a new strategy
    new_strategy = strategist.deploy(
        StrategyVesper, 
        vault,
        vToken,
        pool_rewards,
        1e16,
        0,
        5_000, # 50% percent keep,
        "Vesper LINK"
    )
    new_est_assets_before = new_strategy.estimatedTotalAssets()
    
    vault.migrateStrategy(strategy, new_strategy.address, {"from": gov})
    
    assert new_est_assets_before < new_strategy.estimatedTotalAssets() # New strat should have more assets
    assert strategy.estimatedTotalAssets() < est_assets_before # Old strat should have less assetes
    # set emergency and exit
    new_strategy.setEmergencyExit()
    new_strategy.harvest({"from": strategist})
    
