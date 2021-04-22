# MottoBotto
MottoBotto is a configurable Discord bot with a penchant for mottos and words to live by. It sends nominated mottos to an AirTable base for further use.

## Interacting with MottoBotto

To nominate a motto for consideration, reply to the Discord message with one of MottoBotto's trigger phrases. The default triggers can be found in the [section below](#mottobottos-defaults). MottoBotto will respond to your message with an emoji reaction indicating whether the nomination was accepted, rejected, invalid, or previously nominated.

### Rules MottoBotto follows when accepting mottos

Mottos that are considered valid by MottoBotto are:

* at least two words in length,
* between five and 240 characters in length,
* are not purely punctuation, emoji, or numeric, and
* do not tag any Discord users.

Any suggested motto that doesn't conform to these rules will be responded to with a🙅emoji reaction.

MottoBotto will also reject any nomination that is a statement made by either yourself or MottoBotto.

### Rules humans should follow when suggesting mottos

## Configuring MottoBotto

## MottoBotto's Defaults
Depending on whether MottoBotto is configured to react with words, or with emoji, the defaults are as follows:
- MottoBotto added the nominated motto to the collection: 📥 or "<Nominated motto> will be considered!"
- MottoBotto does not know what you're responding to (i.e. the nominator has forgotten to reply to the motto they are nominating):❓or "I see no motto!"
- MottoBotto has previously added the nominated motto to the collection: ♻️ or ""
- MottoBotto is not allowing itself to be nominated (i.e. the nominated message was written by MottoBotto): ❌ or "Skynet prevention"
- MottoBotto has rejected the motto for motto-fishing (i.e. the motto was written by the nominator): 🎣 or "Motto self-suggestions are forbidden"
- MottoBotto has rejected the motto for violating at least one rule (e.g. the motto is shorter than two words, the motto has a url in it, etc.): 🙅 or ""
