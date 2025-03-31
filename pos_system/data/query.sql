INSERT INTO transactions (
    transaction_id, items, total_amount, final_amount, transaction_date,
    deposit_amount, remaining_amount, client_info
)
SELECT 
    id, items, final_amount AS total_amount, final_amount, 
    date AS transaction_date, deposit_amount, remaining_amount, client_info
FROM transactions_old;