SELECT 
    CS.user_id, 
    S.strategy_name, 
    MAX(T.portfolio_value)
FROM 
    trade T, 
    action A, 
    create_strategy CS, 
    strategy S
WHERE 
    CS.strategy_id = A.strategy_id 
    AND S.strategy_id = CS.strategy_id 
    AND T.trade_id = A.trade_id
GROUP BY 
    CS.user_id, 
    S.strategy_name;
