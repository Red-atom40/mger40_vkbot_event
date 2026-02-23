from domain.quiz import Quiz
from security.encryption import Encryptor
from database.database import Database
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "src")))


DB_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "quiz.db"))
KEY_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "secret.key"))
SEED_COUNT = 500  # сколько заявок создать

FIRST_NAMES = [
    "Александр", "Дмитрий", "Максим", "Иван", "Артём",
    "Анна", "Мария", "Екатерина", "Ольга", "Наталья",
    "Никита", "Сергей", "Владимир", "Елена", "Татьяна",
]

LAST_NAMES = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов",
    "Лебедев", "Козлов", "Новиков", "Морозов", "Петров",
    "Волков", "Соловьёв", "Васильев", "Зайцев", "Павлов",
]

PATRONYMICS = [
    "Александрович", "Дмитриевич", "Иванович", "Сергеевич", "Андреевич",
    "Александровна", "Дмитриевна", "Ивановна", "Сергеевна", "Андреевна",
]

REGIONS = [
    "Московская область", "Ленинградская область", "Краснодарский край",
    "Свердловская область", "Новосибирская область", "Татарстан",
    "Ростовская область", "Челябинская область", "Самарская область",
    "Воронежская область",
]

CITIES = [
    "Москва", "Санкт-Петербург", "Краснодар", "Екатеринбург",
    "Новосибирск", "Казань", "Ростов-на-Дону", "Челябинск",
    "Самара", "Воронеж",
]

STREETS = [
    "ул. Ленина", "ул. Мира", "пр. Победы", "ул. Советская",
    "ул. Гагарина", "ул. Пушкина", "ул. Кирова", "пр. Октября",
    "ул. Садовая", "ул. Центральная",
]

PASSPORT_ISSUER_TEMPLATES = [
    "УМВД России по г. {city}",
    "Отдел МВД России по {city}",
    "ОМВД России по {city}",
]

EDUCATION_LEVELS = [
    "школьное", "среднее специальное", "высшее", "иное",
]

ORGANIZATIONS = [
    "нет",
    "Юнармия",
    "Россия молодая",
    "Волонтёры Победы",
    "РСМ (Российский союз молодёжи)",
    "нет",
]

WORKPLACES = [
    "МГТУ им. Баумана, Москва",
    "СПбГУ, Санкт-Петербург",
    "Уральский федеральный университет, Екатеринбург",
    "ООО «Ромашка», Казань",
    "Школа №5, Краснодар",
    "Московский колледж управления, Москва",
    "ИП Сидоров, Воронеж",
    "АО «Росэнерго», Самара",
]

EMAILS_DOMAINS = ["gmail.com", "mail.ru", "yandex.ru", "inbox.ru"]


def rand_date(start_year: int, end_year: int) -> str:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).strftime("%d.%m.%Y")


def rand_passport_number() -> str:
    series = f"{random.randint(10, 99)}{random.randint(10, 99)}"
    number = f"{random.randint(100000, 999999)}"
    return series + number


def rand_phone() -> str:
    return "+7" + "".join([str(random.randint(0, 9)) for _ in range(10)])


def rand_email(first: str, last: str) -> str:
    domain = random.choice(EMAILS_DOMAINS)
    tag = random.choice(["", str(random.randint(1, 99))])
    return f"{last.lower()}{first[0].lower()}{tag}@{domain}"


def generate_application() -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    patronymic = random.choice(PATRONYMICS)
    city = random.choice(CITIES)

    if patronymic.endswith("на"):
        last = last + "а" if not last.endswith("а") else last

    return {
        "fio": f"{last} {first} {patronymic}",
        "birth_date": rand_date(1990, 2005),
        "region": random.choice(REGIONS),
        "city": city,
        "street": random.choice(STREETS),
        "house": f"{random.randint(1, 200)}" + (f" кв. {random.randint(1, 150)}" if random.random() > 0.4 else ""),
        "passport_number": rand_passport_number(),
        "passport_issued_by": random.choice(PASSPORT_ISSUER_TEMPLATES).format(city=city),
        "passport_issue_date": rand_date(2010, 2022),
        "phone": rand_phone(),
        "contact_info": rand_email(first, last),
        "education_level": random.choice(EDUCATION_LEVELS),
        "is_member": random.choice(["да", "нет", "нет", "нет"]),
        "previous_organizations": random.choice(ORGANIZATIONS),
        "study_or_work_place": random.choice(WORKPLACES),
    }


def main() -> None:
    encryptor = Encryptor(KEY_PATH)
    db = Database(DB_PATH, encryptor)

    created = 0
    skipped = 0

    for i in range(SEED_COUNT):
        vk_id = str(10_000_000 + i)

        if db.has_application(vk_id):
            print(f"  [skip] vk_id={vk_id} — уже существует")
            skipped += 1
            continue

        app = generate_application()
        db.save_application(quiz=Quiz(vk_id=vk_id, **app))
        print(f"  [ok]   vk_id={vk_id} — {app['fio']}")
        created += 1

    print(f"\nГотово: создано {created}, пропущено {skipped}.")


if __name__ == "__main__":
    main()
