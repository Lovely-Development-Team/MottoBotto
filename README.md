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

Any suggested motto that doesn't conform to these rules will be rejected. 

MottoBotto will also reject any nomination that is a statement made by either yourself or MottoBotto.

### Rules humans should follow when suggesting mottos
1. The rules of the server should always be followed, and trump any other rules written here.
2. Aim to nominate mottos that have a useful sentiment rather than solely japes. The aim is to have a useful database of mottos from a variety of users that people can look over and get use from.
3. Do not abuse MottoBotto. Channels should not become spammed with nominations at the expense of the actual conversation that is happening. MottoBotto should aid the discussion, not hinder it.
4. Don’t fish for mottos. While there is a leaderboard, don’t try and cheat the system just to raise up the ranks. Instead, contribute to discussion naturally and helpfully and your reign will come.

## Configuring MottoBotto

## MottoBotto's Defaults
MottoBotto has one recognizable command by default (all others must be added as laid out [above](#configuring-mottobotto)):
* !motto

Depending on whether MottoBotto is configured to react with words, or with emoji, the defaults are as follows:
* MottoBotto added the nominated motto to the collection: 📥 or "'Nominated-motto' will be considered!"
* MottoBotto does not know what you're responding to (i.e. the nominator has forgotten to reply to the motto they are nominating):❓or "I see no motto!"
* MottoBotto has previously added the nominated motto to the collection: ♻️ or ""
* MottoBotto is not allowing itself to be nominated (i.e. the nominated message was written by MottoBotto): ❌ or "Skynet prevention"
* MottoBotto has rejected the motto for motto-fishing (i.e. the motto was written by the nominator): 🎣 or "Motto self-suggestions are forbidden"
* MottoBotto has rejected the motto for violating at least one rule (e.g. the motto is shorter than two words, the motto has a url in it, etc.): 🙅 or ""