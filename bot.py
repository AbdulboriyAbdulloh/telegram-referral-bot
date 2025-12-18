import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from db import (
    init_db, upsert_user, set_full_name, get_full_name,
    top10, get_ref_count
)

# ===== ENV =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@ilimedu")

if not TOKEN or not BOT_USERNAME:
    raise RuntimeError("BOT_TOKEN yoki BOT_USERNAME .env ichida yo‘q!")

# ===== BOT =====
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

init_db()

# ===== STATE =====
class Form(StatesGroup):
    waiting_full_name = State()

# ===== ALT MENYU =====
def bottom_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔗 Referal linkimni olish")
    kb.add("📊 Mening referallarim", "🏆 Top 10")
    kb.add("📢 Kanalga obuna bo‘lish")
    return kb

# ===== HELPERS =====
def valid_full_name(text: str) -> bool:
    return len(text.strip().split()) >= 2

async def is_channel_member(user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ===== START =====
@dp.message_handler(commands=["start"], state="*")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    upsert_user(message.from_user.id, message.from_user.username)

    if not get_full_name(message.from_user.id):
        await message.answer(
            "Turk tilini noldan, professional o‘qituvchilar bilan mutlaqo bepul o‘rganishni xohlaysizmi?\n\n"
            "Agar siz professional o‘qituvchilar yordamida bepul turk tilini o‘rganmoqchi bo‘lsangiz:\n\n"
            "🔹 O‘zingizga tegishli referal (taklif) linkingizni oling\n\n"
            "🔹 Ushbu linkni do‘stlaringiz bilan ulashing va ularni dasturga taklif qiling\n\n"
            "🔹 Sizning referal linkingiz orqali qatnashganlar soni oshgan sari, "
            "bepul turk tili kursida qatnashish huquqiga ega bo‘lasiz\n\n"
            "✅ Qancha ko‘p ulashsangiz, shuncha ko‘p imkoniyat!\n"
            "🏆 Eng ko‘p referal qilgan ishtirokchilar kurslarimizda bepul ta’lim olish huquqini qo‘lga kiritadi.\n\n"
            "📌 Hoziroq referal linkingizni oling va ulashishni boshlang!\n\n"
            "Davom etish uchun iltimos **Ism va Familiyangizni** kiriting.\n"
            "Masalan: Ali Valiyev"
        )
        await Form.waiting_full_name.set()
        return

    await message.answer(
        "📌 Pastdagi menyu orqali davom etishingiz mumkin 👇",
        reply_markup=bottom_menu()
    )

# ===== ISM FAMILIYA =====
@dp.message_handler(state=Form.waiting_full_name)
async def full_name_step(message: types.Message, state: FSMContext):
    if not valid_full_name(message.text):
        await message.answer("❗ Iltimos, ism va familiyani birga kiriting.")
        return

    set_full_name(message.from_user.id, message.text.strip())
    await state.finish()

    await message.answer(
        "✅ Ma’lumotlar saqlandi!\n\nPastdagi menyudan foydalanishingiz mumkin 👇",
        reply_markup=bottom_menu()
    )

# ===== 🔗 REFERAL LINK =====
@dp.message_handler(lambda m: m.text == "🔗 Referal linkimni olish")
async def menu_get_link(message: types.Message):
    user_id = message.from_user.id

    if not await is_channel_member(user_id):
        await message.answer(
            f"❗ Referal link olish uchun avval kanalga obuna bo‘ling:\n{CHANNEL_ID}",
            reply_markup=bottom_menu()
        )
        return

    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    await message.answer(
        "🔗 Bu sizning shaxsiy referal linkingiz.\n\n"
        "Uni do‘stlaringiz bilan ulashing va bepul turk tili kursida "
        "qatnashish imkoniyatini qo‘lga kiriting 👇\n\n"
        f"{ref_link}",
        reply_markup=bottom_menu()
    )

# ===== 📊 MENING REFERALLARIM =====
@dp.message_handler(lambda m: m.text == "📊 Mening referallarim")
async def menu_my_refs(message: types.Message):
    user_id = message.from_user.id

    if not await is_channel_member(user_id):
        await message.answer(
            f"❗ Referal ma’lumotlarni ko‘rish uchun avval kanalga obuna bo‘ling:\n{CHANNEL_ID}",
            reply_markup=bottom_menu()
        )
        return

    count = get_ref_count(user_id)

    await message.answer(
        f"📊 Mening referallarim\n\nSiz taklif qilganlar soni: {count}",
        reply_markup=bottom_menu()
    )

# ===== 🏆 TOP 10 =====
@dp.message_handler(lambda m: m.text == "🏆 Top 10")
async def menu_top10(message: types.Message):
    user_id = message.from_user.id

    if not await is_channel_member(user_id):
        await message.answer(
            f"❗ Top 10 ro‘yxatini ko‘rish uchun avval kanalga obuna bo‘ling:\n{CHANNEL_ID}",
            reply_markup=bottom_menu()
        )
        return

    rows = top10()
    if not rows:
        await message.answer("Hozircha ma’lumot yo‘q.", reply_markup=bottom_menu())
        return

    text = "🏆 TOP 10 ISHTIROKCHILAR\n\n"
    for i, (_, fname, cnt) in enumerate(rows, start=1):
        text += f"{i}. {fname or 'Ismsiz'} — {cnt}\n"

    await message.answer(text, reply_markup=bottom_menu())

# ===== 📢 KANALGA OBUNA =====
@dp.message_handler(lambda m: m.text == "📢 Kanalga obuna bo‘lish")
async def menu_subscribe(message: types.Message):
    await message.answer(
        f"📢 Kanalimizga obuna bo‘ling:\nhttps://t.me/{CHANNEL_ID.lstrip('@')}",
        reply_markup=bottom_menu()
    )

# ===== RUN =====
if __name__ == "__main__":
    print("🤖 Bot ishlayapti (START matni yangilandi)")
    executor.start_polling(dp, skip_updates=True)
