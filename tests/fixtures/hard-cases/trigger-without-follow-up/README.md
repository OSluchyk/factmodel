# trigger-without-follow-up

The shop database's pin moved and the trigger fired, but nobody recorded the follow-up: the triggers stage fails until follow_up_ref is set.

Added so this gate stage has a hard case. Gate: fails `triggers`.
