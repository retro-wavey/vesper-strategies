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
    link_whale = accounts.at("0xbe6977E08D4479C0A6777539Ae0e8fa27BE4e9d6", force=True)
    token.transfer(strategy, 5*1e20,{'from':link_whale})
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
    chain.snapshot()
    vault.updateStrategyDebtRatio(strategy.address, 500, {"from": gov}) # 5%
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

    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    strategy.harvest({"from": strategist})
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    strategy.harvest({"from": strategist}) # All funds to strat
    before = strategy.lossProtectionBalance()
    vault.withdraw(vault.balanceOf(user)/100_000,user,61,{"from": user})
    # Test that user withdraw pulls partially from loss protection
    assert token.balanceOf(strategy) == strategy.lossProtectionBalance()
    assert strategy.lossProtectionBalance() < before

    # Start clean since the debtRatio change test kills our pps
    chain.revert()
    vault.balanceOf(user)
    tx = vault.withdraw(1e6,user,61,{"from": user}) 
    
    tx = vault.withdraw(1e8,user,61,{"from": user})    
    strategy.harvest({"from": strategist})


    # Harvest 4
    print("\n**Harvest 4**")
    chain.sleep(one_day)
    chain.mine(1)
    strategy.harvest({"from": strategist})
    vaultData(vault, token)
    stratData(strategy, token, want_pool, vsp)
    print("Loss Protection Balance:", strategy.lossProtectionBalance())

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

def test_change_debt(gov, wbtc, token, vault, strategy, strategist, amount, user, want_pool):
    # Deposit to the vault and harvest
    token.approve(vault, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    vault.updateStrategyDebtRatio(strategy, 5_000, {"from": gov})
    strategy.harvest({"from": strategist})

    assert strategy.estimatedTotalAssets()+1 == amount / 2

    vault.updateStrategyDebtRatio(strategy, 10_000, {"from": gov})
    strategy.harvest({"from": strategist})
    assert strategy.estimatedTotalAssets()+1 >= amount


def test_sweep(gov, vault, strategy, token, amount, weth, weth_amout, vsp, user):
    # Strategy want token doesn't work
    token.transfer(strategy, amount, {"from": user})
    vsp.transfer(strategy, 1e20, {"from": user})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})

    # TODO: If you add protected tokens to the strategy.
    # Protected token doesn't work
    # with brownie.reverts("!protected"):
    #     strategy.sweep(strategy.protectedToken(), {"from": gov})

    with brownie.reverts("!want"):
         strategy.sweep(token.address, {"from": gov})
    
    with brownie.reverts("!authorized"):
         strategy.sweep(token.address, {"from": user})

    weth.transfer(strategy, weth.balanceOf(gov), {"from": gov})
    assert weth.address != strategy.want()
    strategy.sweep(weth, {"from": gov})
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
