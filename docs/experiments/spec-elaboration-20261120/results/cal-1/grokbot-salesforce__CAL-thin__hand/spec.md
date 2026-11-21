## Use cases

### U-1: A user asks the bot a question and gets an answer
Flow: The user types a question into the bot and the bot replies.
Source: request

## Clauses

### C-1: The bot answers a user's question
Observable: A user types a question and sees an answer.
Source: request

### C-2: The bot is available in the Salesforce org
Observable: A user can find and open the bot.
Source: request

### C-3: Errors are handled gracefully
Observable: The user sees a helpful message when something goes wrong.
Source: implied: by U-1

### C-4: The bot performs well
Observable: The bot responds quickly.
Source: choice: the request does not say
