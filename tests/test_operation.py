import brownie
from brownie import Contract
from helpers import stratData,vaultData


def test_operation(accounts, token, vault, strategy, strategist, amount, user, user2, want_pool, chain, gov, vsp):
    chain.snapshot()
    one_day = 86400
    # Deposit to the vault
    token.approve(vault, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) >= amount
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()

    # harvest 1: funds to strat
    print("\n**Harvest 1**")
    strategy.harvest({"from": strategist})
    chain.mine(1)
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    print("Loss Protection Balance:", strategy.lossProtectionBalance())
    assert strategy.estimatedTotalAssets()+1 >= amount
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()
    
    # Harvest 2: Allow rewards to be earned
    print("\n**Harvest 2**")
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    print("Loss Protection Balance:", strategy.lossProtectionBalance())
    print("\nEst APR: ", "{:.2%}".format(
            ((vault.totalAssets() - amount) * 365) / (amount)
        )
    )
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()

    # Harvest 3
    print("\n**Harvest 3**")
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    print("Loss Protection Balance:", strategy.lossProtectionBalance())
    # Current contract has rewards emissions ending on Mar 19, so we shouldnt project too far
    print("\nEst APR: ", "{:.2%}".format(
            ((vault.totalAssets() - amount) * 365/2) / (amount)
        )
    )
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()

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
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()
    assert before_balance > after_balance
    stratData(strategy, token, want_pool, vsp)

    chain.snapshot()
    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    strategy.harvest({"from": strategist})
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    strategy.harvest({"from": strategist}) # All funds to strat
    before = strategy.lossProtectionBalance()
    vault.withdraw(vault.balanceOf(user)/100_000,user,61,{"from": user})
    # Test that user withdraw pulls from loss protection
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()
    assert strategy.lossProtectionBalance() < before


    
    strategy.harvest({"from": strategist})


    # Harvest 4
    print("\n**Harvest 4**")
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    print("Loss Protection Balance:", strategy.lossProtectionBalance())
    # Current contract has rewards emissions ending on Mar 19, so we shouldnt project too far
    print("\nEst APR: ", "{:.2%}".format(
            ((vault.totalAssets() - amount) * 365/3) / (amount)
        )
    )

    # Harvest 5
    print("\n**Harvest 5**")
    chain.sleep(3600) # wait six hours for a profitable withdraw
    vault.withdraw(vault.balanceOf(user),user,61,{"from": user}) # Need more loss protect to handle 0.6% withdraw fee
    print("After Withdraw - Loss Protection Balance:", strategy.lossProtectionBalance())
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    assert token.balanceOf(user) > amount * 0.994 * .78 # Ensure profit was made after withdraw fee
    assert vault.balanceOf(vault.rewards()) > 0 # Check mgmt fee
    assert vault.balanceOf(strategy) > 0 # Check perf fee
    chain.revert()

def test_switch_dex(accounts, token, vault, strategy, strategist, amount, user, want_pool, chain, gov, vsp):
    originalDex = strategy.activeDex()
    strategy.toggleActiveDex({"from": gov})
    newDex = strategy.activeDex()
    assert originalDex != newDex

def test_emergency_exit(accounts, token, vault, strategy, strategist, amount, user):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() + 1 >= amount

    # set emergency and exit
    strategy.setEmergencyExit()
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets() < amount


def test_profitable_harvest(accounts, token, vault, strategy, strategist, amount, user, chain, want_pool, vsp):
    one_day = 86400
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)

    # harvest 1
    strategy.harvest({"from": strategist})
    chain.mine(1)
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    assert strategy.estimatedTotalAssets()+1 >= amount # Won't match because we must account for withdraw fees

    # Harvest 2: Allow rewards to be earned
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)

    print("\nEst APR: ", "{:.2%}".format(
            ((vault.totalAssets() - amount) * 365) / (amount)
        )
    )
    assert strategy.estimatedTotalAssets()+1 > amount

def test_change_debt(gov, wbtc, wbtc_vault, wbtc_strategy, strategist, amount_wbtc, user, want_pool):
    # Deposit to the vault and harvest
    wbtc.approve(wbtc_vault, amount_wbtc, {"from": user})
    wbtc_vault.deposit(amount_wbtc, {"from": user})
    wbtc_vault.updateStrategyDebtRatio(wbtc_strategy, 5_000, {"from": gov})
    wbtc_strategy.harvest({"from": strategist})

    assert wbtc_strategy.estimatedTotalAssets()+1 == amount_wbtc / 2

    wbtc_vault.updateStrategyDebtRatio(wbtc_strategy, 10_000, {"from": gov})
    wbtc_strategy.harvest({"from": strategist})
    assert wbtc_strategy.estimatedTotalAssets()+1 >= amount_wbtc


def test_sweep(gov, vault, wbtc_strategy, token, amount, weth, weth_amout, vsp, user):
    # Strategy want token doesn't work
    token.transfer(wbtc_strategy, amount, {"from": user})
    vsp.transfer(wbtc_strategy, 1e20, {"from": user})
    assert token.address == wbtc_strategy.want()
    assert token.balanceOf(wbtc_strategy) > 0
    with brownie.reverts("!want"):
        wbtc_strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        wbtc_strategy.sweep(vault.address, {"from": gov})

    # TODO: If you add protected tokens to the strategy.
    # Protected token doesn't work
    # with brownie.reverts("!protected"):
    #     strategy.sweep(strategy.protectedToken(), {"from": gov})

    with brownie.reverts("!want"):
         wbtc_strategy.sweep(token.address, {"from": gov})
    
    with brownie.reverts("!authorized"):
         wbtc_strategy.sweep(token.address, {"from": user})

    weth.transfer(wbtc_strategy, weth.balanceOf(gov), {"from": gov})
    assert weth.address != wbtc_strategy.want()
    wbtc_strategy.sweep(weth, {"from": gov})
    assert weth.balanceOf(gov) > 0


def test_triggers(gov, vault, strategy, token, amount, weth, weth_amout, user, strategist):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    depositAmount = amount
    vault.deposit(depositAmount, {"from": user})
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    strategy.harvest({"from": strategist})
    strategy.harvestTrigger(0)
    strategy.tendTrigger(0)
