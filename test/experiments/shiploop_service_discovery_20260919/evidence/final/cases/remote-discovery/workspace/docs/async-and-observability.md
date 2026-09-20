# Existing operations

ReviewRequest.status is reread by the panel through the existing poller. A
notification, when connected, is only a prompt to reread the durable record.
The identity provider owns successful and failed interactive-login events.
app.audit already reaches the operator event sink for application-owned events;
do not duplicate provider login records there.
