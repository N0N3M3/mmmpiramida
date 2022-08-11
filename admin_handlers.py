import types
from asyncio import sleep

from aiogram.dispatcher import FSMContext
import typing
from config import *
from db.__all_models import *
from states import *
from db import db_session
from main_keyboards import *


@dp.message_handler(commands=['admin'], state='*')
@dp.callback_query_handler(lambda c: c.data == 'admin_panel', state='*')
async def admin_panel_view_admin_handler(message: typing.Union[types.Message, types.CallbackQuery], state: FSMContext):
    await state.finish()
    if message.from_user.id in ADMIN_IDS:
        if isinstance(message, types.CallbackQuery):
            await bot.edit_message_text('Вы в администраторской панели', message.from_user.id,
                                        message.message.message_id, reply_markup=admin_keyboard)
        else:
            await message.answer('Вы в администраторской панели', reply_markup=admin_keyboard)


@dp.callback_query_handler(lambda c: c.data == 'add_tariff', state='*')
async def add_tariff_start_campaign_inline_admin_handler(call: types.CallbackQuery, state: FSMContext):
    await AdminPanel.name_tariff.set()
    await bot.edit_message_text('Введите название тарифа, который хотите добавить', call.from_user.id,
                                call.message.message_id, reply_markup=return_to_main_admin_menu_kb)


@dp.message_handler(state=AdminPanel.name_tariff)
async def about_tariff(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
        await AdminPanel.about_tariff.set()
        await message.answer('Введите описание тарифа', reply_markup=return_to_main_admin_menu_kb)


@dp.message_handler(state=AdminPanel.about_tariff)
async def daily_percent(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        async with state.proxy() as data:
            data['description'] = message.text
            await AdminPanel.daily_percent.set()
            await message.answer('Введите ежедневный процент тарифа', reply_markup=return_to_main_admin_menu_kb)
    else:
        await message.answer('Введите корректное значение')


@dp.message_handler(state=AdminPanel.daily_percent)
async def expire_time_tariff_admin_handler(message: types.Message, state: FSMContext):
    if not message.text.isalpha():
        async with state.proxy() as data:
            data['daily_percent'] = int(message.text)
            await AdminPanel.price_tariff.set()
            await message.answer('Введите стоиомсть тарифа ($)', reply_markup=return_to_main_admin_menu_kb)
    else:
        await message.answer('Введите корректное значение')


@dp.message_handler(state=AdminPanel.price_tariff)
async def price_tariff_admin_handler(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        async with state.proxy() as data:
            with db_session.create_session() as session:
                with session.begin():
                    tariff = Tariff(name=data['name'], description=data['description'],
                                    daily_percent=data['daily_percent'], price=int(message.text))
                    session.add(tariff)
                await state.finish()
                await message.answer('Тариф успешно создан', reply_markup=return_to_main_admin_menu_kb)
                session.commit()
    else:
        await message.answer('Введите корректное значение')


@dp.callback_query_handler(lambda c: c.data.startswith('tariff_detail_view'), state='*')
async def tariff_detail_view_inline_handler(call: types.CallbackQuery):
    tariff_id = int(call.data.split('&')[1])
    with db_session.create_session() as session:
        with session.begin():
            tariff = session.query(Tariff).where(Tariff.tariff_id == tariff_id).first()
            if tariff:
                if tariff.active:
                    text = f"""
                    Тариф №{tariff.tariff_id}
Название: {tariff.name}
Описание: {tariff.description}
Ежедневный процент: {tariff.daily_percent}%
Стоимость тарифа: <b>{tariff.price}</b>$             
                    """
                    kb = types.InlineKeyboardMarkup()
                    if call.from_user.id in ADMIN_IDS:
                        kb.row(
                            types.InlineKeyboardButton('Удалить', callback_data=f'hide_tariff&{tariff.tariff_id}'))
                    kb.row(types.InlineKeyboardButton('Оплатить', callback_data=f'buy_tariff&{tariff.tariff_id}'))
                    await bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=kb)
                    await call.answer()


@dp.callback_query_handler(lambda c: c.data.startswith('buy_tariff'), state='*')
async def buy_tariff(call: types.CallbackQuery):
    tariff_id = int(call.data.split('&')[1])
    with db_session.create_session() as session:
        with session.begin():
            user = session.query(User).where(User.user_id == int(call.from_user.id)).first()
            tariff = session.query(Tariff).where(Tariff.tariff_id == tariff_id).first()
            if user.balance >= tariff.price:
                text = f"""<b>{tariff.name}</b>"""
                await bot.edit_message_text(f'Вы успешно купили тариф: {text}', call.from_user.id,
                                            call.message.message_id, reply_markup=return_to_main_menu_kb)
                user.balance -= tariff.price
                user.subscription = True
                user.user_tariff_id = tariff.name
                user.percent = tariff.daily_percent
            else:
                await bot.edit_message_text(f'Недостаточно средств, пополните баланс',
                                            call.from_user.id, call.message.message_id)


@dp.callback_query_handler(lambda c: c.data.startswith('hide_tariff'), state='*')
async def hide_tariff_inline_admin_handler(call: types.CallbackQuery):
    if call.from_user.id in ADMIN_IDS:
        tariff_id = int(call.data.split('&')[1])
        with db_session.create_session() as session:
            with session.begin():
                tariff = session.query(Tariff).where(Tariff.tariff_id == tariff_id).first()
                tariff.active = False
                text = f'Тариф №{tariff.tariff_id} успешно скрыт.'
                await bot.edit_message_text(text,
                                            call.from_user.id, call.message.message_id,
                                            reply_markup=return_to_main_menu_kb)
                await call.answer()
    else:
        await call.answer('PERMISSION ERROR', show_alert=True)


@dp.callback_query_handler(lambda c: c.data == 'manual_replenishment', state='*')
async def manual_replenishment_inline_admin_handler(call: types.CallbackQuery):
    await AdminPanel.user_id_manual_replenishment.set()
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton('Вернуться назад', callback_data='admin_panel'))
    await bot.edit_message_text('Введите айди пользователя, которому нужно зачислить баланс', call.from_user.id,
                                call.message.message_id, reply_markup=kb)


@dp.message_handler(state=AdminPanel.user_id_manual_replenishment)
async def user_id_manual_replenishment_admin_handler(message: types.Message, state: FSMContext):
    with db_session.create_session() as session:
        with session.begin():
            if not message.text.isalpha():
                user = session.query(User).where(User.user_id == int(message.text)).first()
                if user:
                    async with state.proxy() as data:
                        data['user_id'] = int(message.text)
                    await AdminPanel.summa_manual_replenishment.set()
                    await message.answer('Введите сумму денег для начисления',
                                         reply_markup=return_to_main_admin_menu_kb)
                else:
                    await message.answer('Пользователь не найден. Повторите попытку или отмените операцию',
                                         reply_markup=return_to_main_admin_menu_kb)
            else:
                await message.answer('Некорректный айди. Повторите попытку или отмените операцию',
                                     reply_markup=return_to_main_admin_menu_kb)


@dp.message_handler(state=AdminPanel.summa_manual_replenishment)
async def summa_manual_replenishment_inline_admin_handler(message: types.Message, state: FSMContext):
    with db_session.create_session() as session:
        with session.begin():
            async with state.proxy() as data:
                if not message.text.isalpha():
                    user = session.query(User).where(User.user_id == data['user_id']).first()
                    user.balance += int(message.text)
                    if user.balance < 0:
                        user.balance = 0
                    await state.finish()
                    await message.answer('Баланс пользователя успешно пополнен',
                                         reply_markup=return_to_main_admin_menu_kb)
                else:
                    await message.answer('Некорректная сумма пополнения. Повторите попытку или отмените операцию',
                                         reply_markup=return_to_main_admin_menu_kb)


@dp.callback_query_handler(lambda c: c.data == 'full_info_about_user', state='*')
async def full_info_about_user_start_campaign_inline_admin_handler(call: types.CallbackQuery):
    await AdminPanel.full_info_user_id.set()
    await bot.edit_message_text('Введите ID пользователя', call.from_user.id, call.message.message_id,
                                reply_markup=return_to_main_admin_menu_kb)


@dp.message_handler(state=AdminPanel.full_info_user_id)
async def full_info_about_user_admin_handler(message: types.Message, state: FSMContext):
    with db_session.create_session() as session:
        with session.begin():
            if message.text.isdigit():
                user: User = session.query(User).where(User.user_id == int(message.text)).first()
                if user:
                    await state.finish()
                    text = f"""
Баланс юзера: {int(user.balance)}$
Средств на выводе: {user.hold}$
Тариф юзера: {user.user_tariff_id}
Депозит: {user.deposit}$
Ежедневный процент юзера: {user.percent}%
"""
                    await bot.send_message(message.from_user.id, text)
                else:
                    await message.answer('Пользователь не найден. Повторите попытку или отмените операцию',
                                         reply_markup=return_to_main_admin_menu_kb)
            else:
                await message.answer('Введен некорректный ID. Повторите попытку или отмените операцию',
                                     reply_markup=return_to_main_admin_menu_kb)


@dp.callback_query_handler(lambda c: c.data == 'mailing', state='*')
async def mailing(call: types.CallbackQuery):
    await bot.edit_message_text('Введите текст рассылки', call.from_user.id, call.message.message_id)
    await AdminPanel.mailing_wait.set()


@dp.message_handler(content_types=types.ContentType.ANY, state=AdminPanel.mailing_wait)
async def mailing(message: types.Message, state: FSMContext):
    with db_session.create_session() as session:
        with session.begin():
            users = session.query(User).all()
            for user in users:
                try:
                    await bot.copy_message(chat_id=user.user_id, from_chat_id=message.from_user.id,
                                           message_id=message.message_id)
                    await sleep(0.3)
                except (Exception,):
                    ...
            await message.answer('Рассылка успешно выполнена', reply_markup=return_to_main_admin_menu_kb)
            await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'withdraw_app', state='*')
async def withdraw_app(call: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup()
    with db_session.create_session() as session:
        with session.begin():
            trans = session.query(Transaction)
            for tran in trans:
                if tran.active:
                    kb.row(
                        types.InlineKeyboardButton(f'Заявка №{tran.transaction_id}',
                                                   callback_data=f'tran_detail_view&{tran.transaction_id}'))
        await bot.edit_message_text('Выберите заявку', call.from_user.id,
                                    call.message.message_id, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith('tran_detail_view'), state='*')
async def tran_detail_view_inline_handler(call: types.CallbackQuery):
    tran_id = int(call.data.split('&')[1])
    with db_session.create_session() as session:
        with session.begin():
            tran = session.query(Transaction).where(Transaction.transaction_id == tran_id).first()
            if tran:
                if tran.active:
                    text = f"""
                    Заявка №{tran.transaction_id}
Сумма: {int(tran.amount_money)}$
Юзер: {tran.ordered_the_withdrawal}, @{tran.user_name}
Реквизиты: {tran.requisites}         
                    """
                    kb = types.InlineKeyboardMarkup()
                    if call.from_user.id in ADMIN_IDS:
                        kb.row(
                            types.InlineKeyboardButton('Подтвердить',
                                                       callback_data=f'aceept_tran&{tran.transaction_id}'))
                    kb.row(types.InlineKeyboardButton('Отказать', callback_data=f'decline_tran&{tran.transaction_id}'))
                    kb.row(types.InlineKeyboardButton('В главное меню', callback_data='admin_panel'))
                    await bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith('aceept_tran'), state='*')
async def accept_tran(call: types.CallbackQuery):
    tran_id = int(call.data.split('&')[1])
    with db_session.create_session() as session:
        with session.begin():
            tran = session.query(Transaction).where(Transaction.transaction_id == tran_id).first()
            user = session.query(User).where(User.user_id == tran.ordered_the_withdrawal).first()
            await call.answer('Успешно')
            await bot.send_message(tran.ordered_the_withdrawal, f'Вам подтвердили вывод №{tran.transaction_id}'
                                                                f' на {int(tran.amount_money)}$')
            user.hold -= tran.amount_money
            tran.amount_money = 0
            tran.active = False
            await call.message.edit_reply_markup(return_to_main_admin_menu_kb)


@dp.callback_query_handler(lambda c: c.data.startswith('decline_tran'), state='*')
async def accept_tran(call: types.CallbackQuery):
    tran_id = int(call.data.split('&')[1])
    with db_session.create_session() as session:
        with session.begin():
            tran = session.query(Transaction).where(Transaction.transaction_id == tran_id).first()
            user = session.query(User).where(User.user_id == tran.ordered_the_withdrawal).first()
            await call.answer('Успешно')
            await bot.send_message(tran.ordered_the_withdrawal, f'Отказ на вывод №{tran.transaction_id}'
                                                                f' на {int(tran.amount_money)}$\n'
                                                                f'Средства вернулись на ваш баланс')
            user.hold -= tran.amount_money
            user.balance += tran.amount_money
            tran.amount_money = 0
            tran.active = False
            await call.message.edit_reply_markup(return_to_main_admin_menu_kb)
