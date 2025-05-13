import asyncio

from api.alchemy import AlchemyAPI


async def test_pool_transactions():
    async with AlchemyAPI() as api:
        r1 = await api.get_transaction(
            '4vJfp62jEzcYFnQ11oBJDgj6ZFrdEwcBBpoadNTpEWys',
            'SnJDtXRyFyLyrVEgchR1FFkSQ5pr1cpgAyjx3dmsd7aGgKo4axncgm2iS3WuC1G8s9yPnRv4kAD5nK4GsEAxavR',
        )
        r2 = await api.get_transaction(
            '4vJfp62jEzcYFnQ11oBJDgj6ZFrdEwcBBpoadNTpEWys',
            '5gJ41WH3yGFB3i86zHTitXLwaWuQL6bA2zN2T6W1Ysa6xHeNKH13ts6zBf4G8arB1QHXdoApRW9aq5yJDvrbieo2',
        )
        r3 = await api.get_transaction(
            '4vJfp62jEzcYFnQ11oBJDgj6ZFrdEwcBBpoadNTpEWys',
            '5PD4TrEiT2ts3q7R4MZBUWHcY9XBoq7fvPWMaUJbJx5e2dTVQaT6HUuzaRUiB53GconMSMA9Da7bdkDfvwCsY8rQ',
        )
        r4 = await api.get_transaction(
            '4vJfp62jEzcYFnQ11oBJDgj6ZFrdEwcBBpoadNTpEWys',
            '2PVaD6LLRWC4xaJiSSbmrFcrCmaK1GiFxQbgR7Qg1brfsGsfDLYmAbCBYFETFEBTXHPsPxWJoCcSTdMhwrAQwRkr',
        )
        r5 = await api.get_transaction(
            '5CY89DZjc9nVdwTa8U1VadVsgAh64r78GBoDf3irmW7v',
            '4kfk58wzeVupNtvCTtvLMtVaxGvk99kANXQdEvb9aU3jt3xPJ5Uwg7rZjbGM9m1FP5R6YqYN5CBZxCFnDRDbcCnz',
        )
        print(r1, r2, r3, r4, r5, sep='\n')


asyncio.run(test_pool_transactions())
