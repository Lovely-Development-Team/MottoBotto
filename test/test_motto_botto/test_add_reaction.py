import pytest
from asynctest import Mock, CoroutineMock

from botto import config
from botto.MottoBotto import MottoBotto

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ["word", "emoji"],
    [
        ("success", "📥"),
        ("repeat", "♻️"),
        ("unknown", "❓"),
        ("skynet", "👽"),
        ("fishing", "🎣"),
        ("invalid", "🙅"),
        ("pending", "⏳"),
        ("invalid_emoji", "⚠️"),
        ("valid_emoji", "✅"),
        ("reject", "❌"),
        ("delete_confirmed", "✅"),
    ],
)
async def test_add_reaction(word, emoji):
    # Arrange
    state = Mock()
    state.http = Mock
    state.http.add_reaction = CoroutineMock()

    message = CoroutineMock()

    motto_botto = MottoBotto(config=config.parse({}), mottos=None, members=None)

    # Act
    await motto_botto.add_reaction(message, word)

    # Assert
    message.add_reaction.assert_awaited_once_with(emoji)
