## ctlbot

Simple bot that scrapes for new messages in the nntpchan's ctl (moderation) channel, and sends them to irc if it finds any.

It needs to be split across two scripts because twisted is garbage and you can't have multiple reactors at a time
