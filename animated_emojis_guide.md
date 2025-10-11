# How to Send Animated Emojis with Telethon

Sending animated emojis in Telegram requires more than just copying and pasting the text of a message. Animated emojis are not standard text characters; they are special entities that need to be handled correctly to preserve their animations. This guide explains how to do it using the Telethon library in Python.

## The Problem with Simple Text Copying

When you copy the `.text` attribute of a message, you are only getting the textual representation of the content. The information about the animated emojis is stored separately in the message's `.entities` attribute. If you send only the text, the animation data is lost, and the emojis will appear as static images.

## The Solution: Using Message Entities

To send a message with animated emojis, you need to provide both the text and the formatting entities from the original message. The key is to use the `formatting_entities` parameter in Telethon's `send_message` function.

### Step 1: Fetch the Message

First, you need to get the message object that contains the animated emojis. For example, to get the latest message from your "Saved Messages":

```python
messages = await client.get_messages('me', limit=1)
latest_message = messages[0]
```

### Step 2: Inspect the Message (for debugging)

To understand how the animated emojis are stored, you can inspect the message object. The `entities` attribute will contain a list of `MessageEntityCustomEmoji` objects, one for each animated emoji.

```python
print(latest_message.stringify())
```

This will output the full structure of the message, including the `entities` list, which will look something like this:

```
entities=[
    MessageEntityCustomEmoji(
        offset=0,
        length=2,
        document_id=5427181942934088912
    ),
    # ... more entities
]
```

Each `MessageEntityCustomEmoji` has a `document_id` that uniquely identifies the animated emoji.

### Step 3: Send the Message with Entities

To send a new message with the animated emojis preserved, pass the `formatting_entities` from the original message to the `send_message` function:

```python
await client.send_message(
    'me',  # Or any other recipient
    latest_message.text,
    formatting_entities=latest_message.entities
)
```

By providing the `formatting_entities`, you are telling Telethon to reconstruct the message with the original animated emoji entities, which ensures that they will be animated when the message is sent.