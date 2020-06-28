from get_img import get_img
from get_wiki_answer import get_description
from telegram import ReplyKeyboardMarkup
from data import db_session
from telegram.ext import Updater, MessageHandler, Filters
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler
from story_resource import Story
import os
import random
import logging

if "TOKEN" in os.environ:
    TOKEN = os.environ['TOKEN']
else:
    from config import TOKEN

logging.basicConfig(level=logging.INFO)


# api_url = 'http://localhost:5000'
# api_url = 'https://detective-test.herokuapp.com/'


def start(update, context):
    print('yes')
    context.user_data['in_progress'] = []
    context.user_data['active_story'] = 0
    context.user_data['story_dict'] = {}
    context.user_data['done_stories'] = []
    context.user_data['failed_stories'] = []
    context.user_data['answer'] = ''

    # stories = get(f'{api_url}/api/stories').json()['stories']

    reply_keyboard = [['/stories']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    message = ['Добро пожаловать в Яндекс Детектив!',
               'Здесь Вы сможете погрузиться в жизнь настоящего детектива,',
               'разгадывая загадки и раскрывая преступления.',
               'Вам неизменно будут помогать Ваши коллеги и помощники',
               'Время начинать!',
               '/stories - чтобы получить список историй']
    context.bot.send_photo(
        update.message.chat_id,
        open('static/img/detective_desk.jpg', 'rb'),
        caption='\n'.join(message),
        reply_markup=markup
    )


def stories(update, context):
    # stories = get(f'{api_url}/api/stories').json()['stories']

    session = db_session.create_session()
    stories = [item.to_dict() for item in session.query(Story).all()]
    reply_keyboard = []
    message_text = ['Вам доступны истории:']
    for x in stories:
        reply_keyboard.append([f"/story {x['id']}"])
        if str(x['id']) in context.user_data['done_stories']:
            message_text.append(f"{x['id']} - {x['title']} ✅")
        elif str(x['id']) in context.user_data['failed_stories']:
            message_text.append(f"{x['id']} - {x['title']} ❌")
        else:
            message_text.append(f"{x['id']} - {x['title']}")
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(
        '\n'.join(message_text),
        reply_markup=markup
    )


def story(update, context):
    number = context.args[0]
    reply_keyboard = [['/proof'],
                      ['/spectator'],
                      ['/opinion'],
                      ['/answer'],
                      ['/search']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    # story = get(f'{api_url}/api/stories/{number}').json()['stories']
    session = db_session.create_session()
    story = session.query(Story).get(number).to_dict()
    context.user_data['active_story'] = number
    context.user_data['in_progress'].append(number)
    context.user_data['story_dict'][number] = {'proof': False,
                                               'spectator': False,
                                               'opinion': False}
    help_message = ['/proof - посмотреть улики',
                    '/spectator - опросить очевидцев',
                    '/opinion - спросить мнение коллег',
                    '/answer - дать ответ на задачу',
                    '/search <слово или выражение> - воспользоваться телефоном']
    update.message.reply_text(story['text'])
    update.message.reply_text(
        '\n'.join(help_message),
        reply_markup=markup
    )


def proof(update, context):
    number = context.user_data['active_story']
    if context.user_data['story_dict'][number]['proof']:
        update.message.reply_text('У вас кончились улики')
    else:
        context.user_data['story_dict'][number]['proof'] = True
        session = db_session.create_session()
        # story = get(f'{api_url}/api/stories/{number}').json()['stories']
        story = session.query(Story).get(number).to_dict()
        evidence = story['proof']
        api = story['api']
        # !!!!!ВАРИАНТЫ РАЗЛИЧНЫХ API!!!!!
        if api == 'image':
            map_file = f'static/loaded/{number}.jpg'
            print(map_file)
            # map_file = load_image(evidence, update.message.chat_id)
            if story['api_message']:
                message = story['api_message']
            else:
                message = 'Вам стала доступна фотография с места преступления'
            context.bot.send_photo(
                update.message.chat_id,
                open(map_file, 'rb'),
                caption=message)
        elif api == 'map':
            evidence = str(evidence).split('_')
            for x in evidence:
                map_file = get_img(x)
                context.bot.send_photo(
                    update.message.chat_id,
                    open(map_file, 'rb'))
                os.remove(map_file)
            if story['api_message']:
                message = story['api_message']
                update.message.reply_text(message)

    remains = context.user_data['story_dict'][number]
    reply = []
    if not remains['proof']:
        reply.append('У вас осталась 1 улика \n')
    if not remains['spectator']:
        reply.append('У вас осталось 1 мнение очевидцев \n')
    if not remains['opinion']:
        reply.append('У вас остался 1 диалог с коллегами \n')
    if len(reply) == 0:
        reply.append('У вас больше нет подсказок')
    update.message.reply_text(''.join(reply))


def spectator(update, context):
    number = context.user_data['active_story']
    if context.user_data['story_dict'][number]['spectator']:
        update.message.reply_text('Вы опросили всех очевидцев')
    else:
        session = db_session.create_session()
        story = session.query(Story).get(number).to_dict()
        # story = get(f'{api_url}/api/stories/{number}').json()['stories']
        phrase = story['spectator']
        begins = ['Вам сообщили, что ', 'Вы узнали, что ', 'Опрос показал, что ',
                  'Очевидцы рассказали, что ']
        context.user_data['story_dict'][number]['spectator'] = True
        update.message.reply_text(f'{random.choice(begins)}{phrase}')
    remains = context.user_data['story_dict'][number]
    reply = []
    if not remains['proof']:
        reply.append('У вас осталась 1 улика \n')
    if not remains['spectator']:
        reply.append('У вас осталось 1 мнение очевидцев \n')
    if not remains['opinion']:
        reply.append('У вас остался 1 диалог с коллегами \n')
    if len(reply) == 0:
        reply.append('У вас больше нет подсказок')
    update.message.reply_text(''.join(reply))


def opinion(update, context):
    number = context.user_data['active_story']
    if context.user_data['story_dict'][number]['opinion']:
        update.message.reply_text('Вы опросили всех коллег')
    else:
        session = db_session.create_session()
        story = session.query(Story).get(number).to_dict()
        # story = get(f'{api_url}/api/stories/{number}').json()['stories']
        phrase = story['opinion']
        begins = ['Коллеги думают, что ', 'Вы узнали, что ', 'Ваши друзья думают, что ',
                  'Профессионалы рассказали, что ']
        context.user_data['story_dict'][number]['opinion'] = True
        update.message.reply_text(f'{random.choice(begins)}{phrase}')
    remains = context.user_data['story_dict'][number]
    reply = []
    if not remains['proof']:
        reply.append('У вас осталась 1 улика \n')
    if not remains['spectator']:
        reply.append('У вас осталось 1 мнение очевидцев \n')
    if not remains['opinion']:
        reply.append('У вас остался 1 диалог с коллегами \n')
    if len(reply) == 0:
        reply.append('У вас больше нет подсказок')
    update.message.reply_text(''.join(reply))


def answer(update, context):
    context.user_data['end'] = False
    context.user_data['correct'] = False
    number = context.user_data['active_story']
    # story = get(f'{api_url}/api/stories/{number}').json()['stories']['answer_choice'].split('_')

    session = db_session.create_session()
    story = session.query(Story).get(number).to_dict()['answer_choice'].split('_')
    print(story)

    reply_keyboard = [['/yes'],
                      ['no']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    context.user_data['answer'] = story[0]

    begins = ['Как вы думаете, ', 'По вашему мнению, ', 'Вы считаете, что ', 'Вы думаете, что ']
    update.message.reply_text(
        f'{random.choice(begins)}{story[0]}?',
        reply_markup=markup
    )
    return 1


def first_response(update, context):
    number = context.user_data['active_story']
    if context.user_data['end']:
        reply_keyboard = [[f'/story {number}'],
                          ['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        message = ['Вы можете пройти эту историю заново',
                   'либо перейти к списку историй']
        update.message.reply_text(
            '\n'.join(message),
            reply_markup=markup
        )
        return ConversationHandler.END
    if context.user_data['correct']:
        reply_keyboard = [['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(
            '/stories - к списку историй',
            reply_markup=markup
        )
        return ConversationHandler.END
    # story = get(f'{api_url}/api/stories/{number}').json()['stories']['answer_choice'].split('_')
    session = db_session.create_session()
    story = session.query(Story).get(number).to_dict()['answer_choice'].split('_')

    context.user_data['answer'] = story[1]
    reply_keyboard = [['/yes'],
                      ['no']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    begins = ['Как вы думаете, ', 'По вашему мнению, ', 'Вы считаете, что ', 'Вы думаете, что ']
    update.message.reply_text(
        f'{random.choice(begins)}{story[1]}?',
        reply_markup=markup
    )
    return 2


def second_response(update, context):
    number = context.user_data['active_story']
    if context.user_data['end']:
        reply_keyboard = [[f'/story {number}'],
                          ['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        message = ['Вы можете пройти эту историю заново',
                   'либо перейти к списку историй']
        update.message.reply_text(
            '\n'.join(message),
            reply_markup=markup
        )
        return ConversationHandler.END
    if context.user_data['correct']:
        reply_keyboard = [['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(
            '/stories - к списку историй',
            reply_markup=markup
        )
        return ConversationHandler.END
    # story = get(f'{api_url}/api/stories/{number}').json()['stories']['answer_choice'].split('_')
    session = db_session.create_session()
    story = session.query(Story).get(number).to_dict()['answer_choice'].split('_')
    context.user_data['answer'] = story[2]
    reply_keyboard = [['/yes'],
                      ['no']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    begins = ['Как вы думаете, ', 'По вашему мнению, ', 'Вы считаете, что ', 'Вы думаете, что ']
    update.message.reply_text(
        f'{random.choice(begins)}{story[2]}?',
        reply_markup=markup
    )
    return 3


def third_response(update, context):
    number = context.user_data['active_story']
    if context.user_data['end']:
        reply_keyboard = [[f'/story {number}'],
                          ['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        message = ['Вы можете пройти эту историю заново',
                   'либо перейти к списку историй']
        update.message.reply_text(
            '\n'.join(message),
            reply_markup=markup
        )
        return ConversationHandler.END
    if context.user_data['correct']:
        reply_keyboard = [['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(
            '/stories - к списку историй',
            reply_markup=markup
        )
        return ConversationHandler.END
    # story = get(f'{api_url}/api/stories/{number}').json()['stories']['answer_choice'].split('_')
    session = db_session.create_session()
    story = session.query(Story).get(number).to_dict()['answer_choice'].split('_')
    context.user_data['answer'] = story[3]
    reply_keyboard = [['/yes'],
                      ['no']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    begins = ['Как вы думаете, ', 'По вашему мнению, ', 'Вы считаете, что ', 'Вы думаете, что ']
    update.message.reply_text(
        f'{random.choice(begins)}{story[3]}?',
        reply_markup=markup
    )
    return 4


def fourth_response(update, context):
    number = context.user_data['active_story']
    if context.user_data['end']:
        reply_keyboard = [[f'/story {number}'],
                          ['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        message = ['Вы можете пройти эту историю заново',
                   'либо перейти к списку историй']
        update.message.reply_text(
            '\n'.join(message),
            reply_markup=markup
        )
        return ConversationHandler.END
    if context.user_data['correct']:
        reply_keyboard = [['/stories']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(
            '/stories - к списку историй',
            reply_markup=markup
        )
        return ConversationHandler.END
    # story = get(f'{api_url}/api/stories/{number}').json()['stories']['answer_choice'].split('_')
    session = db_session.create_session()
    story = session.query(Story).get(number).to_dict()['answer_choice'].split('_')
    context.user_data['answer'] = story[4]
    reply_keyboard = [['/yes']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    begins = ['Как вы думаете, ', 'По вашему мнению, ', 'Вы считаете, что ', 'Вы думаете, что ']
    update.message.reply_text(
        f'{random.choice(begins)}{story[4]}?',
        reply_markup=markup
    )
    update.message.reply_text(
        'Это последний вопрос, других версий у Вас нет',
        reply_markup=markup
    )


def agree(update, context):
    number = context.user_data['active_story']
    session = db_session.create_session()
    right_answer = session.query(Story).get(number).to_dict()['answer']
    # right_answer = get(f'{api_url}/api/stories/{number}').json()['stories']['answer']
    if right_answer == context.user_data['answer']:
        reply_keyboard = [['/exit']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text('Правильно!')
        update.message.reply_text('/exit - закончить историю',
                                  reply_markup=markup)
        context.user_data['correct'] = True
        context.user_data['done_stories'].append(number)
        return ConversationHandler.END
    else:
        reply_keyboard = [['/repeat']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        message = ['Увы, нет ☹️',
                   '/repeat - попытаться заново']
        update.message.reply_text(
            '\n'.join(message),
            reply_markup=markup
        )
        context.user_data['end'] = True
        context.user_data['failed_stories'].append(number)
        return ConversationHandler.END


def search(update, context):
    obj = ' '.join(context.args)
    description = get_description(obj)
    update.message.reply_text(description)


def main():
    print('Connect...')

    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start',
                                  start,
                                  pass_user_data=True))

    dp.add_handler(CommandHandler('stories',
                                  stories,
                                  pass_user_data=True))

    dp.add_handler(CommandHandler('story',
                                  story,
                                  pass_args=True,
                                  pass_user_data=True))

    dp.add_handler(CommandHandler('proof',
                                  proof,
                                  pass_user_data=True))

    dp.add_handler(CommandHandler('spectator',
                                  spectator,
                                  pass_user_data=True))

    dp.add_handler(CommandHandler('opinion',
                                  opinion,
                                  pass_user_data=True))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('answer', answer, pass_user_data=True)],

        states={
            1: [MessageHandler(Filters.text, first_response)],
            2: [MessageHandler(Filters.text, second_response)],
            3: [MessageHandler(Filters.text, third_response)],
            4: [MessageHandler(Filters.text, fourth_response)]
        },

        fallbacks=[CommandHandler('yes', agree),
                   CommandHandler('search', search, pass_args=True)]
    )

    dp.add_handler(CommandHandler('yes', agree))
    dp.add_handler(CommandHandler('search', search, pass_args=True))
    dp.add_handler(conv_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    db_session.global_init()
    # session = db_session.create_session()
    # stories = session.query(Story).all()
    # session.close()
    # for i in range(len(stories)):
    #     print(i)
    #     story = stories[i].to_dict()
    #     session = db_session.create_session()
    #     new = Story(
    #         id=None,
    #         title=story['title'],
    #         text=story['text'],
    #         answer=story['answer'],
    #         spectator=story['spectator'],
    #         opinion=story['opinion'],
    #         api=story['api'],
    #         proof=story['proof'],
    #         api_message=story['api_message'],
    #         answer_choice=story['answer_choice']
    #     )
    #     session.add(new)
    #     session.commit()
    main()
