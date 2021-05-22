# TODO: Add tests that show proper migration of the strategy to a newer one
#       Use another copy of the strategy to simulate the migration
#       Show that nothing is lost!


def test_migration(token, vault, strategy, StrategyVesper, want_pool, pool_rewards, vsp, uni_router, sushi_router, amount, strategist, gov, user, chain):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    strategy.harvest({"from": strategist})
    est_assets_before = strategy.estimatedTotalAssets()
    assert strategy.estimatedTotalAssets()+1 == amount
    chain.sleep(10000)
    chain.mine(1)

    # migrate to a new strategy
    new_strategy = strategist.deploy(
        StrategyVesper, 
        vault,
        want_pool,
        pool_rewards,
        vsp,
        uni_router,
        sushi_router,
        1e16,
        False
    )
    new_est_assets_before = new_strategy.estimatedTotalAssets()

    strategy.migrate(new_strategy.address, {"from": gov})
    
    assert new_est_assets_before < new_strategy.estimatedTotalAssets() # New strat should have more assets
    assert strategy.estimatedTotalAssets() < est_assets_before # Old strat should have less assetes
    

