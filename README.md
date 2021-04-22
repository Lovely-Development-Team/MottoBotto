# MottoBotto
MottoBotto is a configurable Discord bot with a penchant for mottos and words to live by. It sends nominated mottos to an AirTable base for further use.

## Default Usage TLDR

* Nominate somebody else's message as a potential motto with `!motto` in a reply to the message.
* Change your leaderboard emoji with a direct message to MottoBotto of `!emoji <new-emoji>`.

## Interacting with MottoBotto

To nominate a motto for consideration, reply to the Discord message with one of MottoBotto's trigger phrases. **It is highly recommended to disable the @ ping for these replies!** The default triggers can be found in the [section below](#motto-nomination). MottoBotto will respond to your message with an emoji reaction indicating whether the nomination was accepted, rejected, invalid, or previously nominated.

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

### Adding or changing your emoji on the leaderboard

To add an emoji to your name on the leaderboard, change the emoji, or remove it, use the [change emoji trigger](#change-emoji) in a direct message to MottoBotto. The default is `!emoji`:

* `!emoji 🚀` will set the ​🚀​ emoji for your user.
* `!emoji` will clear any emoji for your user.

MottoBotto will respond with a reaction indicating a successful update or a problem with your request.

## Configuring MottoBotto

MottoBotto requires a `config.json` configuration file, with the following sections.

| Section          | Key             | Default Value                    | Required | Description                                                  |
| ---------------- | --------------- | -------------------------------- | -------- | ------------------------------------------------------------ |
| `authentication` | `discord`       | Empty string                     | Yes      | MottoBotto's DIscord bot token.                              |
|                  | `airtable_key`  | Empty string                     | Yes      | The API key for access to Airtable's API.                    |
|                  | `airtable_base` | Empty string                     | Yes      | The ID of the Airtable base to store the mottos.             |
| `channels`       | `exclude`       | Empty list                       | No       | A list of Discord channel names to ignore when reacting to triggers. |
|                  | `include`       | Empty list                       | No       | A list of Discord channels to specifically respond to triggers within. If specified, all other channels are ignored. |
| `reactions`      | `success`       | See below.                       | No       | The emoji to react to a successful nomination with.          |
|                  | `repeat`        | See below.                       | No       | The emoji to react to a nomination that has already been nominated with. |
|                  | `skynet`        | See below.                       | No       | The emoji to react to a nomination of a MottoBotto message with. |
|                  | `fishing`       | See below.                       | No       | The emoji to react to a nomination of the user's own message with. |
|                  | `invalid`       | See below.                       | No       | The emoji to react to invalid nominations with.              |
|                  | `invalid_emoji` | See below.                       | No       | The emoji to react to invalid emoji updates with.            |
|                  | `valid_emoji`   | See below.                       | No       | The emoji to react to successful emoji updates with.         |
| `should_reply`   | N/A             | `true`                           | No       | Whether to send message replies in response to nomations or not. If `false`, the only notifications users will receive are emoji reactions on their nomination message. |
| `rules`          | `matching`      | `^.{5,240}$`<br />`^(\S+\s+)\S+` | No       | A list of regular expressions to match against the nominated motto text that must all match for the motto to accepted. The message is first stripped of leading and trailing whitespace before matching. * |
|                  | `excluding`     | `<@.*>`<br />`^[\d\W\s]*$`       | No       | A list of regular expressions to match against the nominated motto text, where any successful match will result in an invalid motto response. The message is first stripped of leading and trailing whitespace before matching. * |
| `triggers`       | `new_motto`     | `!motto$`                        | No       | A list of regular expressions to match against every incoming message in the relevant channels (see `channels` above) to recognise a new nomination. They are all prepended with `^` before matching, to ensure they match the start of the message. The message is first stripped of leading and trailing whitespace before matching. * |
|                  | `change_emoji`  | `!emoji`                         | No       | A list of regular expressions to match against every incoming direct message to recognise a request to change the user's emoji. They are all prepended with `^` before matching, to ensure they match the start of the message. The message is first stripped of leading and trailing whitespace before matching. * |

\*Note: Regular expressions used for motto nomination rule matching are matched with case sensitivity, and must include the `^` and `$` if you wish to match against the entire message string. Those used for trigger phrases are matched without regard for case.

### Example configuration

The following is a full example `config.json`.

```json
{
    "authentication": {
        "discord": "REDACTED",
        "airtable_key": "REDACTED",
        "airtable_base": "REDACTED"
    },
    "channels": {
        "exclude": [
            "ignore-this-channel"
        ]
    },
    "rules": {
        "excluding": [
          "^HELLO!$"
        ]
    },
    "reactions": {
        "success": "📥",
        "repeat": "♻️",
        "unknown": "❓",
        "skynet": "❌",
        "fishing": "🎣"
    },
    "triggers": {
        "new_motto": [
            "!motto$",
	          "Accurate[.,!] New motto\\?"
        ]
    },
    "should_reply": false
}
```

## MottoBotto Defaults
### Trigger Phrases

The trigger phrases detailed below are the defaults.  Any others for each trigger must be added as laid out [above](#configuring-mottobotto).

#### Motto Nomination

`!motto`

MottoBotto will always react with emoji, but can also be configured to react with a text message response. The defaults for both are as follows, although the emoji reactions can be changed in configuration:
* 📥 MottoBotto added the nominated motto to the collection: "'Nominated-motto' will be considered!"
* ❓ MottoBotto does not know what you're responding to (i.e. the nominator has forgotten to reply to the motto they are nominating): "I see no motto!"
* ♻️ MottoBotto has previously added the nominated motto to the collection. There is currently no text reply for this situation.
* ❌ MottoBotto is not allowing itself to be nominated (i.e. the nominated message was written by MottoBotto): "Skynet prevention"
* 🎣 MottoBotto has rejected the motto for motto-fishing (i.e. the motto was written by the nominator): "Motto self-suggestions are forbidden"
* 🙅 MottoBotto has rejected the motto for violating at least one rule (e.g. the motto is shorter than two words, the motto has a url in it, etc.) There is currently no text reply for this situation.

#### Change Emoji

`!emoji`

This trigger phrase **must be sent as a direct message to MottoBotto**. If followed by an emoji (such as `!emoji 🚀`, it will set the user's emoji in the leaderboard to the specified emoji. If no emoji is specified, it will clear the emoji from the leaderboard for that user. It will only work for standard emoji, and not server-specific custom emoji.

MottoBotto will respond to the message with one of two reactions (the emoji for which can be changed in configuration). The defaults are as follows:

* ✅ The user's emoji was successfully updated.
* ⚠️ The emoji specified is not valid.

## Licensing

This code is copyright the contributors.

[MottoBotto is licensed under the Mozilla Public License 2.0](LICENSE)

### MottoBotto's Profile Image
Robot and Scroll Emoji Copyright 2020 Twitter, Inc and other contributors and licensed under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)