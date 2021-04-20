from discord import Message, ClientUser


def is_botto(message: Message, botto_user: ClientUser):
    # In case someone convinces Botto to say "!motto"
    if message.author == botto_user:
        return True
    # Message has no reference, so it can't be Botto
    elif not message.reference:
        return False
    # We don't know what message is being referenced, so assume it wasn't us.
    # This probably isn't a safe assumption, the check should be elsewhere
    # and future versions should attempt to resolve messages
    if message.reference.resolved is None:
        return False
    # If reference message is from Botto
    elif message.reference.resolved.author == botto_user:
        return True
    else:
        return False
