---
bump: minor
---
Fix forward: a send-back no longer reruns finished steps. A step whose document was accepted (reviewed and committed)
stays done: its commit, review and test counts stand, and nothing rebuilds it. The amended step plan starts with the
done steps' rows exactly as written, each marked `"done": true`, which the step-plan packet prints to copy, then at
least one step still to run. A fix to finished work is a new step with new criterion IDs, and test cases due at a
finished step stay as accepted. ShipLoop refuses an amendment or test spec that reopens a done step.
