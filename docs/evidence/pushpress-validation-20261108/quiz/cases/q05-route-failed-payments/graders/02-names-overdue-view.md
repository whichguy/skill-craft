---
type: regex
target: last_message
match: contains
flags: i
weight: 1
---

(Invoices[^\n]{0,80}Overdue|Overdue[^\n]{0,80}(?:Invoices|Open)|/payments\b|/reports/payments|Payments Forecast)
