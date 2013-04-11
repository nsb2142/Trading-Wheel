-- need to integrate with new row in strategy for start date. also need to create the new row.
MERGE INTO aggregate_portfolio A
		USING (
		select s1.start_value as start_cash, 100000 as start_port, 0 as start_sec, s.strategy_id, ag.portfolio_id, time
			from day_to_day dtd, aggregate_portfolio ag, strategy s
			where ag.portfolio_id = dtd.portfolio_id
				AND s.strategy_id = dtd.strategy_id
				AND time = (SELECT min(time)
					from day_to_day dtd1, aggregate_portfolio ag1, strategy s1
					where ag1.portfolio_id = dtd1.portfolio_id
						AND s1.strategy_id = dtd1.{0}
						AND s1.strategy_id = s.{0})
		) B
		ON (B.portfolio_id = A.portfolio_id)
		WHEN MATCHED THEN UPDATE SET A.free_cash = B.start_cash, A.securites_value = B.start_sec, A.portfolio_value = B.start_port;