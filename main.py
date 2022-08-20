import telebot, requests, sqlite3, time
from bs4 import BeautifulSoup
from telebot import types
from config import BOT_TOKEN


bot = telebot.TeleBot(BOT_TOKEN)

url = "https://context.reverso.net/translation/"
language_from = ''
language_to = ''
word = ''
lang_template = ['Arabic', 'German', 'English', 'Spanish', 'French', 'Hebrew', 'Japanese', \
                 'Dutch', 'Polish', 'Portuguese', 'Romanian', 'Russian', 'Turkish'] # available languages


@bot.message_handler(commands=['start'])
def start(message):
  # Connect Data base
  connect = sqlite3.connect('user_requests.db')
  curs = connect.cursor()

  # Create a db
  curs.execute("""CREATE TABLE IF NOT EXISTS user_id(
    u_id INTEGER
    join_date TEXT
  )""")
  connect.commit()

  # Check id in db
  cache_id = message.chat.id
  curs.execute(f"SELECT u_id FROM user_id WHERE u_id = {cache_id}")
  data = curs.fetchone()
  if data is None:
    #Add some info in db
    user_data = [message.chat.id, time.ctime(time.time())]
    curs.execute("INSERT INTO `user_id` (`u_id`, `join_date`) VALUES(?, ?);", (user_data[0], user_data[1]))
    connect.commit()
    # Creating ReplyKeyboard
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn = types.KeyboardButton("Что ты умеешь?")
    markup.add(btn)
    mess = f"Hello {message.from_user.first_name} ✌."
    bot.send_message(message.chat.id, mess, parse_mode="html", reply_markup=markup)
  else:
    bot.send_message(message.chat.id, f"Dear {message.from_user.first_name}, we've already met:)")


@bot.message_handler(commands=['help'])
def commands(message):
  mess = """My abilities:
/start - Launch
/help - My commands
/translate - Start translating
/history - Your requests history"""
  bot.send_message(message.chat.id, mess, parse_mode="html")

@bot.message_handler(commands=['translate'])
def language(message):
  mess = """Available languages:
• Arabic 
• German 
• English 
• Spanish 
• French 
• Hebrew 
• Japanese 
• Dutch 
• Polish 
• Portuguese 
• Romanian 
• Russian 
• Turkish
  
What language do you want to translate from?
  """
  msg = bot.send_message(message.chat.id, mess, parse_mode="html")
  bot.register_next_step_handler(msg, tr_language_from)


def tr_language_from(message):
  if (message.text).title() in lang_template:
    global language_from
    language_from = message.text.title()
    msg = bot.send_message(message.chat.id, f"You've chosen the first language: {language_from}\nEnter the language you want to translate into:")
    bot.register_next_step_handler(msg, tr_language_to)
  else:
    msg = bot.send_message(message.chat.id, "Enter the language from the suggested list", parse_mode="html")
    bot.register_next_step_handler(msg, tr_language_from)


def tr_language_to(message):
  if (message.text).title() in lang_template:
    global language_to
    language_to = message.text.title()
    msg = bot.send_message(message.chat.id, f"You have chosen a second language: {language_to}\nEnter a word/sentence to translate:")
    bot.register_next_step_handler(msg, translate)
  else:
    msg = bot.send_message(message.chat.id, "Enter the language from the suggested list", parse_mode="html")
    bot.register_next_step_handler(msg, tr_language_to)


def translate(message):
  global word
  word = message.text.split()
  url = f"https://context.reverso.net/translation/{language_from.lower()}-{language_to.lower()}/"
  if len(word) !=1:
    for i in range(len(word)):
      if i == len(word)-1:
        url += f"{word[i]}"
      else:
        url += f"{word[i]}+"
  else:
    url += f'{word[0]}'
  print(url)
  headers = {'User-Agent': 'Mozilla/5.0'}
  r = requests.get(url, headers=headers)
  if r.status_code == 404:
     msg = bot.send_message(message.chat.id, f"Sorry, but the word {word} cannot be translated..\nPlease enter the correct word", parse_mode="html")
     bot.register_next_step_handler(msg, translate)
  elif r.status_code != 200:
    bot.send_message(message.chat.id, f"Something is wrong with your internet connection..", parse_mode="html")
    exit()
  response = r
  soup = BeautifulSoup(response.content, 'html.parser')
  translations = []
  answer = ''
  if len(word) != 1:
    sentence_examples = []
    for sentence in soup.find(id="examples-content").select(".ltr"):
      sentence_examples.append(sentence.text.strip())
    for i in range(10):
      if i % 2 == 0 and i != 0:
        answer += (f"\n{sentence_examples[i]}\n")
      else:
        answer += (f"{sentence_examples[i]}\n")
  else:
    for words in soup.find(id='translations-content').select('.display-term'):
      translations.append(words.text.strip())
      if len(translations) == 5:
        break
    for i in range(len(translations)):
      answer += f"{translations[i]}\n"

  # db operations
  connect = sqlite3.connect('user_requests.db')
  curs = connect.cursor()
  curs.execute("""CREATE TABLE IF NOT EXISTS user_req(
        u_id INTEGER
        req_date TEXT
        lang TEXT
        text TEXT
      )""")
  connect.commit()
  if translations:
    req_data = [message.chat.id, time.ctime(time.time()), f"{language_from}\\{language_to} for {word}", f"{translations[0]}"]
  else:
    req_data = [message.chat.id, time.ctime(time.time()), f"{language_from}\\{language_to} for {word}", f"{sentence_examples[0]}\\{sentence_examples[1]}"]
  # Add some info in db
  curs.execute("INSERT INTO `user_req` (`u_id`, `req_date`, `lang`, `text`) VALUES(?, ?, ?, ?);", (req_data[0], req_data[1], req_data[2], req_data[3]))
  connect.commit()

  # print translation
  print(answer)
  bot.send_message(message.chat.id, answer, parse_mode="html")


@bot.message_handler(commands=['history'])
def history(message):
  connect = sqlite3.connect('user_requests.db')
  curs = connect.cursor()
  mess = "Your requests:\n"
  curs.execute(f"SELECT * FROM user_req WHERE u_id = {message.chat.id}")
  items = curs.fetchall()
  for element in items:
    mess += f"\n{element[2]} - {element[3]}\n"
  bot.send_message(message.chat.id, mess, parse_mode="html")

@bot.message_handler(content_types=['text'])
def buttons_text(message):
  if message.text == 'Что ты умеешь?':
    mess = "My name is Ben and I can translate anything you want into 20 different languages!\nJust write the command /help and you will learn about my functionality:)"
    bot.send_message(message.chat.id, mess, parse_mode="html" )
  else:
    bot.send_message(message.chat.id, "Choose one of my commands:\n/start - I'm starting up\n/help - Output of my commands\n/translate - Start translation")




bot.polling(none_stop=True) #launching bot