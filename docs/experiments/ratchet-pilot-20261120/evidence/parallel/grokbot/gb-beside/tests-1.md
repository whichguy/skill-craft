## Failing now

none

## Discoveries

- An otherwise enabled action attempted while another save is awaiting acknowledgement should indicate whether it was accepted, deferred or blocked. | Observable: Delay the Save instruction response, then open New bot, enter a name and activate Save bot name before releasing the response. | Why: Save bot name remained enabled, but the click sent no request, showed no feedback and created no bot.
