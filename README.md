# antiburner-bot
Telegram bot for antiburner


## python-telegram-bot latest version package installation

```bash
virtualenv -p python3 venv
source venv/bin/activate
git clone https://github.com/python-telegram-bot/python-telegram-bot
cd python-telegram-bot/
python setup.py install
```

## python-telegram-bot usage examples

```python
chat_id = update.message.chat_id
# chat_id = update.effective_chat.id
received_message_id = update.message.message_id
```

```python
send_message = await context.bot.send_message(
	chat_id=update.effective_chat.id,
	text="text of message",
	parse_mode=ParseMode.MARKDOWN_V2
)
```

```python
await context.bot.delete_message(
	chat_id=update.message.chat_id,
	message_id=update.message.message_id
)
```

```python
await context.bot.edit_message_text(
	text="new text of message",
	chat_id=update.effective_chat.id,
	message_id=m_id # from store
)
```

## Команды бота

```
board - Вывести доску
wide_board - Вывести широкую доску
# ticket_delete - Удаление указанных записей
```