from security.encryptor import Encryptor
from config import Config
import argparse
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


FIRST_NAMES = [
    "Александр", "Дмитрий", "Максим", "Иван", "Артём",
    "Анна", "Мария", "Екатерина", "Ольга", "Наталья",
    "Никита", "Сергей", "Владимир", "Елена", "Татьяна",
    "Олег", "Павел", "Виктор", "Юлия", "Алексей",
    "Михаил", "Григорий", "Валерия", "Светлана", "Кирилл",
    "Анастасия", "Владислав", "Ирина", "Денис", "Евгений",
    "Марина", "Валентин", "Галина", "Роман", "Людмила",
]

LAST_NAMES = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов",
    "Лебедев", "Козлов", "Новиков", "Морозов", "Петров",
    "Волков", "Соловьёв", "Васильев", "Зайцев", "Павлов",
    "Лебедев", "Козлов", "Новиков", "Морозов", "Соколов",
    "Васильев", "Зайцев", "Павлов", "Лебедев", "Козлов",
    "Новиков", "Морозов", "Соколов", "Васильев", "Зайцев",
    "Павлов", "Лебедев", "Козлов", "Новиков", "Морозов",
    "Соколов", "Васильев", "Зайцев", "Павлов", "Лебедев",
    "Козлов", "Новиков", "Морозов", "Соколов", "Васильев",
]

PATRONYMICS = [
    "Александрович", "Дмитриевич", "Иванович", "Сергеевич", "Андреевич",
    "Александровна", "Дмитриевна", "Ивановна", "Сергеевна", "Андреевна",
    "Максимович", "Максимовна", "Артёмович", "Артёмовна", "Никитич", "Никитична",
    "Владимирович", "Владимировна", "Еленович", "Еленовна", "Татьянович", "Татьяновна",
    "Ольгович", "Ольговна", "Натальевич", "Натальевна",
    "Петрович", "Петровна", "Волкович", "Волковна", "Соловьёвич", "Соловьёвна",
    "Васильевич", "Васильевна", "Зайцевич", "Зайцевна", "Павлович", "Павловна",
    "Лебедевич", "Лебедевна", "Козлович", "Козловна", "Новикович", "Новиковна",
    "Морозович", "Морозовна", "Соколович", "Соколова",
]

REGIONS = [
    "Московская область", "Ленинградская область", "Краснодарский край",
    "Свердловская область", "Новосибирская область", "Татарстан",
    "Ростовская область", "Челябинская область", "Самарская область",
    "Воронежская область", "Ульяновская область", "Нижегородская область", "Пермский край",
    "Волгоградская область", "Красноярский край", "Саратовская область", "Тюменская область", "Иркутская область", "Томская область",
    "Кемеровская область", "Рязанская область", "Оренбургская область",
]

CITIES = [
    "Москва", "Санкт-Петербург", "Краснодар", "Екатеринбург",
    "Новосибирск", "Казань", "Ростов-на-Дону", "Челябинск",
    "Самара", "Воронеж", "Уфа", "Нижний Новгород", "Пермь", "Волгоград",
    "Красноярск", "Саратов", "Тюмень", "Ижевск", "Барнаул", "Ульяновск",
    "Иркутск", "Томск", "Кемерово", "Рязань", "Оренбург",
]

STREETS = [
    "ул. Ленина", "ул. Мира", "пр. Победы", "ул. Советская",
    "ул. Гагарина", "ул. Пушкина", "ул. Кирова", "пр. Октября",
    "ул. Садовая", "ул. Центральная", "ул. Молодёжная", "ул. Школьная", "ул. Лесная", "ул. Набережная",
    "ул. Комсомольская", "ул. Первомайская", "ул. Лермонтова", "ул. Чехова", "ул. Вокзальная",
    "ул. Солнечная", "ул. Цветочная", "ул. Заречная", "ул. Лазурная", "ул. Берёзовая",
]

PASSPORT_ISSUER_TEMPLATES = [
    "УМВД России по г. {city}",
    "Отдел МВД России по {city}",
    "ОМВД России по {city}",
]

EDUCATION_LEVELS = [
    "школьное", "среднее специальное", "высшее", "иное", "нет",
]

ORGANIZATIONS = [
    "нет",
    "Юнармия",
    "Россия молодая",
    "Волонтёры Победы",
    "РСМ (Российский союз молодёжи)",
    "нет",
    "Движение первых",
    "Молодая гвардия Единой России",
    "Российское движение школьников",
    "Студенческие отряды",
    "Молодёжный парламент при Государственной Думе",
    "Молодёжный парламент при Правительстве РФ",
    "Молодёжный парламент при региональном правительстве",
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
    "ГБУ «Здоровье», Челябинск",
    "нет",
    "ДВФУ",
    "МГУ",
    "НИУ ВШЭ",
    "СПбПУ",
    "КФУ",
    "ТГУ",
    "РАНХиГС",
    "Газпром",
    "Росатом",
    "РЖД",
]

CONTACTS_DOMAINS = ["smth@gmail.com", "smth@mail.ru", "smth@yandex.ru", "smth@inbox.ru",
                    "smth@outlook.com", "smth@protonmail.com", "@username", "@nickname,", "@smth"]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def generate_user(vk_id: int) -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    patronymic = random.choice(PATRONYMICS)
    fio = f"{last} {first} {patronymic}"

    birth = random_date(date(1975, 1, 1), date(2008, 12, 31))

    city = random.choice(CITIES)
    region = random.choice(REGIONS)
    street = random.choice(STREETS)
    house = f"{random.randint(1, 200)}" + (
        f" корп. {random.randint(1, 5)}" if random.random() < 0.3 else ""
    ) + (
        f" кв. {random.randint(1, 300)}" if random.random() < 0.7 else ""
    )

    passport_series = f"{random.randint(10, 99)}{random.randint(10, 99)}"
    passport_number = f"{random.randint(100000, 999999)}"
    passport_full = passport_series + passport_number

    issuer_template = random.choice(PASSPORT_ISSUER_TEMPLATES)
    passport_issued_by = issuer_template.format(city=city)

    passport_issue_date = random_date(date(1997, 1, 1), date(2024, 12, 31))
    while passport_issue_date < birth + timedelta(days=14 * 365):
        passport_issue_date = random_date(date(1997, 1, 1), date(2024, 12, 31))

    phone = "7" + "".join(str(random.randint(0, 9)) for _ in range(10))

    contact = random.choice(CONTACTS_DOMAINS)
    if contact.startswith("@"):
        name_part = first.lower() + str(random.randint(1, 999))
        contact = contact.replace("smth", name_part).rstrip(",")
    else:
        name_part = first.lower() + str(random.randint(1, 999))
        contact = contact.replace("smth", name_part)

    education = random.choice(EDUCATION_LEVELS)
    is_member = random.choice(["да", "нет"])
    organizations = random.choice(ORGANIZATIONS)
    workplace = random.choice(WORKPLACES)

    created_at = random_date(date(2024, 1, 1), date(2026, 2, 24))

    return {
        "vk_id": vk_id,
        "fio": fio,
        "birth_date": fmt_date(birth),
        "region": region,
        "city": city,
        "street": street,
        "house": house,
        "passport_number": passport_full,
        "passport_issued_by": passport_issued_by,
        "passport_issue_date": fmt_date(passport_issue_date),
        "phone": phone,
        "contact_info": contact,
        "education_level": education,
        "is_member": is_member,
        "previous_organizations": organizations,
        "study_or_work_place": workplace,
        "created_at": created_at.strftime("%Y-%m-%d"),
    }


def seed(config_path: str, count: int) -> None:
    config = Config(Path(config_path))
    encryptor = Encryptor(config.key_path)

    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            vk_id                   INTEGER PRIMARY KEY,
            fio                     TEXT NOT NULL,
            birth_date              TEXT NOT NULL,
            region                  TEXT NOT NULL,
            city                    TEXT NOT NULL,
            street                  TEXT NOT NULL,
            house                   TEXT NOT NULL,
            passport_number         TEXT NOT NULL,
            passport_issued_by      TEXT NOT NULL,
            passport_issue_date     TEXT NOT NULL,
            phone                   TEXT NOT NULL,
            contact_info            TEXT NOT NULL,
            education_level         TEXT NOT NULL,
            is_member               TEXT NOT NULL,
            previous_organizations  TEXT NOT NULL,
            study_or_work_place     TEXT NOT NULL,
            created_at              REAL NOT NULL
        );
    """)

    inserted = 0
    skipped = 0
    vk_id = 100_000_001

    while inserted < count:
        user = generate_user(vk_id)
        vk_id += 1

        encrypted_passport = encryptor.encrypt(user["passport_number"])
        try:
            conn.execute(
                """
                INSERT INTO applications (
                    vk_id, fio, birth_date, region, city, street, house,
                    passport_number, passport_issued_by, passport_issue_date,
                    phone, contact_info, education_level, is_member,
                    previous_organizations, study_or_work_place, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["vk_id"],
                    user["fio"],
                    user["birth_date"],
                    user["region"],
                    user["city"],
                    user["street"],
                    user["house"],
                    encrypted_passport,
                    user["passport_issued_by"],
                    user["passport_issue_date"],
                    user["phone"],
                    user["contact_info"],
                    user["education_level"],
                    user["is_member"],
                    user["previous_organizations"],
                    user["study_or_work_place"],
                    user["created_at"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    conn.close()
    print(
        f"Готово: вставлено {inserted}, пропущено {skipped} (уже существовали).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Наполнить БД тестовыми заявками")
    parser.add_argument("--count", type=int, default=500,
                        help="Количество записей (по умолчанию 500)")
    parser.add_argument("--config", default="config.json",
                        help="Путь к config.json")
    args = parser.parse_args()

    seed(args.config, args.count)
